from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import UploadedFile
from app.tools.document_reader import detect_file_type, parse_local_document


async def save_uploaded_file(db: Session, task_id: int, upload: UploadFile) -> UploadedFile:
    filename = Path(upload.filename or "uploaded-file").name
    file_type = detect_file_type(filename)
    content = await upload.read()

    if len(content) > settings.upload_max_bytes:
        raise ValueError(f"File exceeds max upload size: {settings.upload_max_bytes} bytes")

    task_dir = settings.upload_dir / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    stored_path = task_dir / f"{uuid4().hex}-{filename}"
    stored_path.write_bytes(content)

    parsed_text = parse_local_document(stored_path, settings.reader_max_chars)
    uploaded_file = UploadedFile(
        task_id=task_id,
        filename=filename,
        file_path=str(stored_path),
        file_type=file_type,
        parsed_text=parsed_text,
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def list_uploaded_files(db: Session, task_id: int) -> list[UploadedFile]:
    statement = select(UploadedFile).where(UploadedFile.task_id == task_id).order_by(UploadedFile.id)
    return list(db.scalars(statement))
