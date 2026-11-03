


import os
import shutil
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException, status

MEDIA_DIR = "app/media"
ALLOW_MINE = ["image/png", "image/jpeg"]
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
CHUNKS = 1024 * 1024
    
def ensure_media_dir() -> None:
    os.makedirs(MEDIA_DIR, exist_ok=True)
    
def save_uploaded_file(file: UploadFile) -> dict:
    if file.content_type not in ALLOW_MINE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only png jpeg images"
        )
    
    ensure_media_dir()
    ext = os.path.splitext(file.filename)[1] #jpeg or png
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    class _ChunkCounter:
        def __init__(self, f):
            self._f = f
            self.calls = 0
            self.sizes = []
        def read(self, n=-1):
            data = self._f.read(n)
            if data:
                self.calls += 1
                self.sizes.append(len(data))
            return data
        def __getattr__(self, name):  # delega cualquier otro atributo
            return getattr(self._f, name)

    reader = _ChunkCounter(file.file)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(reader, buffer, length=CHUNKS)
    
    size = os.path.getsize(file_path)
    if size > MAX_MB * 1024 *1024:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File to heavy (>{MAX_MB} MB)"
        )
    
    
    return {
        "filename": filename,
        "content_type": file.content_type,
        "url": f"/media/{filename}",
        # "size": size,
        # "chunk_size_used": CHUNKS,
        # "chunk_calls": reader.calls,
        # "chunk_size_samples": reader.sizes[5]
    }