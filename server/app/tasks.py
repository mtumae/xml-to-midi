import os
import subprocess
import time
from uuid import UUID

import boto3
from config import settings
from database import engine
from models.files import Files
from models.logs import Logs
from video.render import VideoRender
from botocore import retries
from celery import Celery
from sqlmodel import Session

app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)


r2 = boto3.client(
    service_name="s3",
    endpoint_url=settings.R2_ENDPOINT,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


@app.task(bind=True, max_retries=3)
def convert_chunk(self, file_id: str, chunk_index: str, r2_chunk_key: str):
    """
    Converts one singular chunk into mp4

    Args:
        file_id (str): The ID of the file being processed.
        r2_raw_key (str): The raw key for the R2 bucket.
    """
    local_input_xml = f"/tmp/{file_id}_chunk_{chunk_index}.musicxml"
    local_output_mp4 = f"/tmp/{file_id}_render_{chunk_index}.mp4"
    r2_rendered_chunk_key = (
        f"{settings.R2_BUCKET}/temp/{file_id}/rendered_chunks/part_{chunk_index}.mp4"
    )
    message = ""

    # update file status to converting
    with Session(engine) as session:
        file = session.get(Files, file_id)
        if file:
            file.status = "converting"
            session.add(file)
            session.commit()

    s_time = time.perf_counter()
    try:
        # call video conversion
        VideoRender(
            local_input_xml,
            file_id,
            chunk_index,
            local_output_mp4,
            r2_rendered_chunk_key,
        ).start()
        e_time = time.perf_counter()
        elapsed = e_time - s_time
        message = f"Converted chunk {chunk_index} of file {file_id[:5]}... in {elapsed:.2f}(s)"
        print(message)
        with Session(engine) as session:
            file = session.get(Files, file_id)
            if file:
                log = Logs(file_id=file_id, log_message=message)
                file.status = "converted"
                session.add(file)
                session.add(log)
            session.commit()

    except Exception as e:
        message = (
            f"Failed to convert chunk {chunk_index} of file {file_id[:5]}: {str(e)}"
        )
        print(message)
        with Session(engine) as session:
            log = Logs(file_id=file_id, log_message=message)
        session.add(log)
        session.commit()
        raise e

    finally:
        for path in [local_input_xml, local_output_mp4]:
            if os.path.exists(path):
                os.remove(path)
