"""
Excel Upload Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional

router = APIRouter()


@router.post("/")
async def upload_excel(file: UploadFile = File(...), group_name: Optional[str] = None):
    """Upload LINE group Excel file"""
    # Validate file extension
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    # TODO: Implement upload logic
    return {
        "status": "success",
        "message": f"File {file.filename} uploaded successfully",
        "group_name": group_name,
    }
