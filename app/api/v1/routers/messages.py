"""
Line Messages Upload / Import Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import Optional, List
from csv import reader as csv_reader

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.group_service import GroupService
from app.services.message_service import MessageService

router = APIRouter()


class ExcelType:
    QA_MESSAGE = "qa_message"
    LINE_MESSAGE = "line_message"


@router.post("/")
async def upload_excel(
    file: UploadFile = File(...),
    group_uniid: str = None,
    excel_type: str = ExcelType.LINE_MESSAGE,
    db: Session = Depends(get_db),
):
    """Upload Excel/CSV and import into `line_messages` depending on `excel_type`."""
    # basic validation
    if excel_type != ExcelType.LINE_MESSAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported excel_type: {excel_type}",
        )

    # Accept XLSX/XLS
    fname = file.filename.lower()
    if not fname.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    # Ensure group exists (use group_uniid as uniid if provided)
    gsvc = GroupService()
    grp = gsvc.get_by_uniid(db, group_uniid)
    if not grp:
        raise HTTPException(status_code=404, detail="group_uniid not found")

    msg_svc = MessageService()
    created = 0

    try:
        import openpyxl

        wb = openpyxl.load_workbook(filename=file.file, read_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        headers = None
        for i, row in enumerate(rows):
            if i == 0:
                headers = [str(c).strip() if c is not None else "" for c in row]
                continue
            data = {
                headers[j]: row[j] if j < len(row) else None
                for j in range(len(headers))
            }
            params = {}
            if grp:
                params["group_id"] = grp.id
            elif "group_id" in data and data["group_id"]:
                try:
                    params["group_id"] = int(data["group_id"])
                except Exception:
                    pass
            params["message_content"] = (
                data.get("message_content") or data.get("content") or None
            )
            params["message_uid"] = data.get("message_uid")
            msg_svc.create_message(db, **params)
            created += 1
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Processing xlsx requires 'openpyxl' package. Install it to enable xlsx support.",
        )

    db.commit()

    return {
        "status": "success",
        "message": f"Imported {created} records for type {excel_type}",
        "group": {"id": grp.id, "uniid": grp.uniid, "name": grp.name} if grp else None,
    }
