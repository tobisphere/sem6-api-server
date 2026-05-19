import os
import glob
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

api = FastAPI(title="Fast API")

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://raspberrypi.tail1480d1.ts.net"
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = "/api/uploads"

# Ensure the upload directory exists within the container
os.makedirs(UPLOAD_DIR, exist_ok=True)

@api.get("/")
async def root():
    return {"message": "FastAPI is running. Ready for uploads."}

@api.get("/api/fetch")
async def fetch_file():
    # Find all png files in the upload dir
    files = glob.glob(os.path.join(UPLOAD_DIR, "*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="No photos found.")
    # Get the most recent one based on modification time
    latest_file = max(files, key=os.path.getmtime)
    return FileResponse(
        path=latest_file,
        media_type='image/png',
        filename=os.path.basename(latest_file)
    )

@api.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts a file and saves it to the local mounted volume.
    """
    try:
        # Sanitize filename to prevent directory traversal attacks
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        # Check if file already exists to avoid overwriting (optional logic)
        if os.path.exists(file_location):
            base, ext = os.path.splitext(file.filename)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            file_location = f"{base}_{counter}{ext}"

        with open(file_location, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return {
            "filename": file.filename,
            "size": len(content),
            "path": file_location,
            "message": "File uploaded successfull."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@api.get("/health")
async def health_check():
    return {"status": "healthy", "storage_path": UPLOAD_DIR}

