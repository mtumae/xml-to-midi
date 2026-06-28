import os
import time
from typing import Annotated
from uuid import UUID

import boto3
import dotenv
from config import settings
from database import get_session
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, UploadFile
from models.files import Files
from pydantic import BaseModel
from sqlalchemy.orm import Session
from tasks import convert_chunk

dotenv.load_dotenv()


class InitUploadRequest(BaseModel):
    file_name: str
    total_chunks: int


class CompleteUploadRequest(BaseModel):
    file_id: str
    file_name: str
    chunk_keys: list[
        str
    ]  # e.g., ["projects/raw/123/chunk_0.xml", "projects/raw/123/chunk_1.xml"]


r2_endpoint_url = settings.R2_ENDPOINT
r2_aws_access_key_id = settings.R2_ACCESS_KEY_ID
r2_aws_secret_access_key = settings.R2_SECRET_ACCESS_KEY
r2_bucket = settings.R2_BUCKET

r2 = boto3.client(
    service_name="s3",
    endpoint_url=r2_endpoint_url,
    aws_access_key_id=r2_aws_access_key_id,
    aws_secret_access_key=r2_aws_secret_access_key,
    region_name="auto",
)

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/status/{file_id}")
async def get_file_status(file_id: UUID, session: Session = Depends(get_session)):
    file = session.get(Files, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File tracking record not found")

    return {
        "status": file.status,
        "progress": f"{file.converted_chunks}/{file.total_chunks}",
    }


@router.get("/get/{file_id}")
async def get_file(file_id: UUID, session: Session = Depends(get_session)):
    file = session.get(Files, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "file": {
            "id": file.id,
            "status": file.status,
            "r2_raw_key": file.r2_raw_key,
            "r2_output_key": file.r2_output_key,
            "created_at": file.created_at,
            "updated_at": file.updated_at,
        }
    }
