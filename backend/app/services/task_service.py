from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentStep, Note, Report, Source, Task, TaskStatus
from app.schemas.task import TaskCreate


def create_task(db: Session, payload: TaskCreate) -> Task:
    title = payload.title or payload.user_query[:40]
    task = Task(title=title, user_query=payload.user_query, status=TaskStatus.pending)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int) -> Task | None:
    return db.get(Task, task_id)


def list_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.created_at.desc())))


def list_steps(db: Session, task_id: int) -> list[AgentStep]:
    statement = select(AgentStep).where(AgentStep.task_id == task_id).order_by(AgentStep.id)
    return list(db.scalars(statement))


def list_sources(db: Session, task_id: int) -> list[Source]:
    statement = select(Source).where(Source.task_id == task_id).order_by(Source.id)
    return list(db.scalars(statement))


def list_notes(db: Session, task_id: int) -> list[Note]:
    statement = select(Note).where(Note.task_id == task_id).order_by(Note.id)
    return list(db.scalars(statement))


def get_latest_report(db: Session, task_id: int) -> Report | None:
    statement = select(Report).where(Report.task_id == task_id).order_by(Report.created_at.desc())
    return db.scalars(statement).first()
