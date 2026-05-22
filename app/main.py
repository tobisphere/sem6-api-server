import glob
import hashlib
import io
import os
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

app = FastAPI(title="Fast API")

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:57391",
    "https://raspberrypi.tail1480d1.ts.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "../uploads"
MAX_IMAGES = 3
MODEL_PATH = "model/resnet18_sketch_model.pth"
KNOWN_UNSAFE_HASHES = set()
BLOCKED_WORDS = [
    "sex",
    "porn",
    "nigger",
    "niga",
    "nazi",
    "rape",
    "terrorist",
    "kill",
    "suicide",
    "fuck",
    "bitch",
    "slur",
    "nsfw",
]

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_image_hash(image_bytes):
    return hashlib.md5(image_bytes).hexdigest()


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


model = models.resnet18(weights=None)

model.fc = nn.Linear(model.fc.in_features, 2)

model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device("cpu")))

model.eval()
transform = transforms.Compose(
    [
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

labels = ["safe", "unsafe"]


@app.get("/")
async def root():
    return {"message": "FastAPI is running. Ready for uploads."}


@app.get("/app/fetch")
async def fetch_file():
    files = glob.glob(os.path.join(UPLOAD_DIR, "*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="No photos found.")
    latest_file = max(files, key=os.path.getmtime)
    return FileResponse(
        path=latest_file, media_type="image/png", filename=os.path.basename(latest_file)
    )


@app.get("/app/fetch_all")
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
        image_list.append(
            {
                "filename": os.path.basename(file_path),
                "path": file_path,
                "size_bytes": stat.st_size,
                "modified_timestamp": stat.st_mtime,
                "modified_datetime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/app/fetch",
            }
        )
    image_list.sort(key=lambda x: x["modified_timestamp"], reverse=True)
    return {"images": image_list, "total": len(image_list), "limit": MAX_IMAGES}


@app.post("/app/upload")
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
                    num_str = basename.split("_")[-1].replace(".png", "")
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
            "message": "File uploaded successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@app.post("app/predict")
async def predict_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image_hash = get_image_hash(image_bytes)
        lower_name = file.filename.lower()
        if image_hash in KNOWN_UNSAFE_HASHES:
            return JSONResponse(
                {
                    "prediction": "unsafe",
                    "confidence": 1.0,
                    "reason": "known_unsafe_image",
                }
            )
        for word in BLOCKED_WORDS:
            if word in lower_name:
                KNOWN_UNSAFE_HASHES.add(image_hash)
                return JSONResponse(
                    {
                        "prediction": "unsafe",
                        "confidence": 1.0,
                        "reason": f"blocked_word:{word}",
                    }
                )
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_tensor = transform(image)
        image_tensor = image_tensor.unsqueeze(0)
        with torch.no_grad():
            outputs = model(image_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
        prediction = labels[predicted.item()]
        confidence_score = round(confidence.item(), 4)
        if confidence_score < 0.75:
            prediction = "review_required"
        if prediction == "unsafe":
            KNOWN_UNSAFE_HASHES.add(image_hash)
        return JSONResponse({"prediction": prediction, "confidence": confidence_score})
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/health")
async def health_check():
    return {"status": "healthy", "storage_path": UPLOAD_DIR, "model_path": MODEL_PATH}
