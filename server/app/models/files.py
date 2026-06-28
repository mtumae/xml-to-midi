from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FilesBase(SQLModel):  # Not sure why this exists, move it later
    original_filename: str
    total_chunks: int


class Files(FilesBase, table=True):
    __table_args__ = {"schema": "public"}
    id: str = Field(default_factory=uuid4, primary_key=True, index=True)
    status: str = Field(
        default="queued"
    )  # queued, converting, storing, complete, failed
    r2_raw_key: Optional[str] = Field(default=None)
    r2_output_key: Optional[str] = Field(default=None)
    converted_chunks: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
