import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path

api = FastAPI(title="Fast API")

# Configuration
UPLOAD_DIR = "/app/uploads"

# Ensure the upload directory exists within the container
os.makedirs(UPLOAD_DIR, exist_ok=True)

@api.get("/")
async def root():
    return {"message": "FastAPI is running. Ready for uploads."}

@api.post("/upload")
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
