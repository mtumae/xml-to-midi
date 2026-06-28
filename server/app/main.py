from contextlib import asynccontextmanager
from typing import Annotated

from config import settings
from database import engine, verify_db_connection, get_session
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models import files, logs
from routes import uploads, files
from sqlmodel import SQLModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup")
    # verify_db_connection()
    # get_session()
    #SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1", debug=True, lifespan=lifespan)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.include_router(uploads.router)
app.include_router(files.router)



app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/", response_class=HTMLResponse)
def serve_spa():
    with open("templates/index.html", "r") as f:
        return f.read()


@app.get("/api/health", tags=["health"])
def read_root():
    return {
        "status": "online",
        "application": settings.APP_NAME,
        "message": "File processing gateway is running smoothly.",
    }
