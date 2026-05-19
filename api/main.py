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

UPLOAD_DIR = "/api/uploads"
MAX_IMAGES = 3

os.makedirs(UPLOAD_DIR, exist_ok=True)

@api.get("/")
async def root():
    return {"message": "FastAPI is running. Ready for uploads."}

@api.get("/api/fetch")
async def fetch_file():
    files = glob.glob(os.path.join(UPLOAD_DIR, "*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="No photos found.")
    latest_file = max(files, key=os.path.getmtime)
    return FileResponse(
        path=latest_file,
        media_type='image/png',
        filename=os.path.basename(latest_file)
    )


@api.get("/api/fetch_all")
async def fetch_all_images():
    """
    Returns a list of all files in the upload directory.
    """
    pattern = os.path.join(UPLOAD_DIR, "photo_*.png")
    files = glob.glob(pattern)
    if not files:
        return {"images": [], "total": 0, "message": "No images found."}
    image_list = []
    for file_path in files:
        stat = os.stat(file_path)
        image_list.append({
            "filename": os.path.basename(file_path),
            "path": file_path,
            "size_bytes": stat.st_size,
            "modified_timestamp": stat.st_mtime,
            "modified_datetime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "url": f"/api/fetch"
        })
    image_list.sort(key=lambda x: x["modified_timestamp"], reverse=True)
    return {
        "images": image_list,
        "total": len(image_list),
        "limit": MAX_IMAGES
    }

@api.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts a file and saves it.
    """
    try:
        existing_files = glob.glob(os.path.join(UPLOAD_DIR, "photo_*.png"))
        if existing_files:
            numbers = []
            for f in existing_files:
                basename = os.path.basename(f)
                try:
                    num_str = basename.split('_')[-1].replace('.png', '')
                    numbers.append(int(num_str))
                except ValueError:
                    continue
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1

        new_filename = f"photo_{next_num}.png"
        file_location = os.path.join(UPLOAD_DIR, new_filename)

        content = await file.read()
        with open(file_location, "wb") as buffer:
            buffer.write(content)

        deleted_count = cleanup_old_images()
        return {
            "original_filename": file.filename,
            "new_filename": new_filename,
            "size": len(content),
            "path": file_location,
            "deleted_old_files": deleted_count,
            "message": "File uploaded successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@api.get("/health")
async def health_check():
    return {"status": "healthy", "storage_path": UPLOAD_DIR}

def cleanup_old_images():
    """
    Removes the oldest image if the total count exceeds MAX_IMAGES.
    Returns the number of files removed.
    """
    pattern = os.path.join(UPLOAD_DIR, "photo_*.png")
    files = glob.glob(pattern)
    if len(files) <= MAX_IMAGES:
        return 0
    oldest_file = min(files, key=os.path.getmtime)
    try:
        os.remove(oldest_file)
        print(f"Deleted oldest image to make room: {os.path.basename(oldest_file)}")
        return 1
    except OSError as e:
        print(f"Error deleting file {oldest_file}: {e}")
        return 0
