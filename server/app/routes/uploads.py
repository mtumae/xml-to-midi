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

router = APIRouter(prefix="/api/upload", tags=["uploads"])


@router.post("/init")
async def initiate_upload(
    request: InitUploadRequest, session: Session = Depends(get_session)
):
    import uuid

    file_id = str(uuid.uuid4())
    file_name, file_ext = request.file_name.rsplit(".", 1)

    presigned_urls = []
    chunk_keys = []
    for i in range(request.total_chunks):
        r2_chunk_key = f"raw/{file_id}/chunk_{i}.{file_ext}"
        chunk_keys.append(r2_chunk_key)
        url = r2.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": r2_bucket,
                "Key": r2_chunk_key,
                "ContentType": f"application/{file_ext}",
            },
            ExpiresIn=3600,  # expires in 1 hour
        )
        presigned_urls.append(url)
        print(f"[api/upload/init]: Chunk={i+1}/{request.total_chunks} uploaded successfully.")

    return {
        "file_id": file_id,
        "urls": presigned_urls,
        "chunk_keys": chunk_keys,
    }


@router.post("/complete")
async def complete_upload(
    request: CompleteUploadRequest, session: Session = Depends(get_session)
):
    new_file = Files(
        id=request.file_id,
        original_filename=request.file_name,
        status="queued",
        # r2_raw_key=request.r2_raw_key,
        total_chunks=len(request.chunk_keys),
        r2_output_key=None,
        converted_chunks=0,
    )
    session.add(new_file)
    session.commit()

    request.chunk_keys # Array of ["projects/raw/{file_id}/chunk_0.xml", ...]

    print(f"[complete_upload]: Added file_id={request.file_id[:5]}... to database")

    # Its Celery time
    # parallel_tasks = [
    #         convert_chunk.s(file_id=request.file_id, chunk_index=i, r2_chunk_key=key)
    #         for i, key in enumerate(request.chunk_keys)
    #     ]

    return {
        "file_id": new_file.id,
        "status": "success",
        "message": "File queued for conversion",
    }



@router.get("/health", tags=["health"])
def health_check():
    return {
        "status": "online",
        "application": settings.APP_NAME,
        "message": "Uploads route is online.",
    }
