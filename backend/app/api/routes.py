from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agent.workflow import run_research
from app.db.models import TaskStatus
from app.db.session import SessionLocal, get_db
from app.schemas.task import (
    AgentStepRead,
    MemoryRead,
    MemorySearchRequest,
    MemorySearchResult,
    NoteRead,
    ReportCitationRead,
    ReportRead,
    RagChunkRead,
    RagSearchRequest,
    SourceRead,
    TaskCreate,
    TaskRead,
    UploadedFileRead,
)
from app.services.citation_service import list_report_citations
from app.services.file_service import list_uploaded_files, save_uploaded_file
from app.services.memory_service import list_memories, search_memories
from app.services.research_intent import assess_research_intent
from app.services.rag_service import retrieve_relevant_chunks
from app.services.task_service import (
    create_task,
    get_latest_report,
    get_task,
    list_notes,
    list_sources,
    list_steps,
    list_tasks,
)

router = APIRouter()


def run_task_in_background(task_id: int) -> None:
    with SessionLocal() as db:
        task = get_task(db, task_id)
        if task is None:
            return
        run_research(db, task)


@router.post("/tasks", response_model=TaskRead)
def create_research_task(payload: TaskCreate, db: Session = Depends(get_db)):
    intent = assess_research_intent(payload.user_query)
    if not intent.is_research:
        raise HTTPException(status_code=400, detail=intent.message)
    return create_task(db, payload)


@router.get("/tasks", response_model=list[TaskRead])
def read_tasks(db: Session = Depends(get_db)):
    return list_tasks(db)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/run", response_model=dict)
def run_task(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    intent = assess_research_intent(task.user_query)
    if not intent.is_research:
        return {"task_id": task_id, "status": task.status, "skipped": True, "message": intent.message}
    if task.status != TaskStatus.running:
        task.status = TaskStatus.running
        db.commit()
        background_tasks.add_task(run_task_in_background, task_id)
    return {"task_id": task_id, "status": task.status}


@router.post("/tasks/{task_id}/files", response_model=UploadedFileRead)
async def upload_task_file(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        return await save_uploaded_file(db, task_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/files", response_model=list[UploadedFileRead])
def read_task_files(task_id: int, db: Session = Depends(get_db)):
    return list_uploaded_files(db, task_id)


@router.post("/tasks/{task_id}/rag/search", response_model=list[RagChunkRead])
def search_task_rag(task_id: int, payload: RagSearchRequest, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return retrieve_relevant_chunks(db, task_id, payload.query, payload.top_k)


@router.get("/memories", response_model=list[MemoryRead])
def read_memories(db: Session = Depends(get_db)):
    return list_memories(db)


@router.post("/memories/search", response_model=list[MemorySearchResult])
def search_memory(payload: MemorySearchRequest, db: Session = Depends(get_db)):
    return search_memories(db, payload.query, payload.top_k)


@router.get("/tasks/{task_id}/steps", response_model=list[AgentStepRead])
def read_steps(task_id: int, db: Session = Depends(get_db)):
    return list_steps(db, task_id)


@router.get("/tasks/{task_id}/sources", response_model=list[SourceRead])
def read_sources(task_id: int, db: Session = Depends(get_db)):
    return list_sources(db, task_id)


@router.get("/tasks/{task_id}/notes", response_model=list[NoteRead])
def read_notes(task_id: int, db: Session = Depends(get_db)):
    return list_notes(db, task_id)


@router.get("/tasks/{task_id}/report", response_model=ReportRead)
def read_report(task_id: int, db: Session = Depends(get_db)):
    report = get_latest_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/tasks/{task_id}/citations", response_model=list[ReportCitationRead])
def read_report_citations(task_id: int, db: Session = Depends(get_db)):
    return list_report_citations(db, task_id)
