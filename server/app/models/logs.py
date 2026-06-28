from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import declared_attr
from sqlmodel import Field, SQLModel


class Logs(SQLModel, table=True):
    __table_args__ = {"schema": "public"}
    id: str = Field(default_factory=uuid4, primary_key=True, index=True)
    # status: str = Field(
    #     default="queued"
    # )  # queued, converting, storing, complete, failed
    file_id: str = Field()
    log_message: str = Field()
    created_at: datetime = Field(default_factory=datetime.now)
