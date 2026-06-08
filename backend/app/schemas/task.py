from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str | None = None
    user_query: str


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    user_query: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    step_type: str
    input: dict
    output: dict
    status: str
    error_message: str | None
    duration_ms: int | None
    created_at: datetime


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    title: str
    url: str
    content_summary: str
    source_type: str
    created_at: datetime


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    filename: str
    file_path: str
    file_type: str
    parsed_text: str
    created_at: datetime


class RagSearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class RagChunkRead(BaseModel):
    id: int
    task_id: int
    source_id: int | None
    chunk_index: int
    content: str
    metadata: dict
    distance: float


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int | None
    content: str
    memory_type: str
    tags: list[str]
    created_at: datetime


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class MemorySearchResult(BaseModel):
    id: int
    task_id: int | None
    content: str
    memory_type: str
    tags: list[str]
    distance: float
    created_at: datetime


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    source_id: int | None
    content: str
    tags: list[str]
    created_at: datetime


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    markdown_content: str
    created_at: datetime


class ReportCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    report_id: int
    source_id: int | None
    chunk_id: int | None
    citation_index: int
    title: str
    url: str
    quote: str
    created_at: datetime
