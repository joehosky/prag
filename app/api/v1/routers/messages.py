"""
Line Messages Upload / Import Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import Optional, List
from enum import Enum
from csv import reader as csv_reader

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.group_service import GroupService
from app.services.message_service import MessageService

router = APIRouter()


class ExcelType(str, Enum):
    QA_MESSAGE = "qa_message"
    LINE_MESSAGE = "line_message"


@router.post("/")
async def upload_excel(
    file: UploadFile = File(...),
    group_uniid: str = None,
    excel_type: ExcelType = ExcelType.LINE_MESSAGE,
    db: Session = Depends(get_db),
):
    """Upload Excel/CSV and import into `line_messages` or `qa_messages` depending on `excel_type`."""

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

    # Helper: parse workbook into headers + data rows
    def _parse_xlsx(file_obj):
        import openpyxl

        wb = openpyxl.load_workbook(filename=file_obj, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return [], []
        headers = [str(c).strip() if c is not None else "" for c in rows[0]]
        data_rows = rows[1:]
        return headers, data_rows

    # Handler for line_message type (existing behavior)
    def _import_line_messages(db, msg_svc, grp, headers, data_rows):
        created = 0
        for row in data_rows:
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
        return created

    # Handler for qa_message type (imports question/answer pairs)
    def _import_qa_messages(db, msg_svc, grp, headers, data_rows):
        created = 0
        for row in data_rows:
            data = {
                headers[j]: row[j] if j < len(row) else None
                for j in range(len(headers))
            }
            question = data.get("question") or data.get("q") or data.get("prompt")
            answer = data.get("answer") or data.get("a") or data.get("response")
            uid = data.get("message_uid") or data.get("uid") or None

            if question:
                params = {"message_content": question, "message_uid": uid}
                if grp:
                    params["group_id"] = grp.id
                msg_svc.create_message(db, **params)
                created += 1

            if answer:
                params = {
                    "message_content": answer,
                    "message_uid": (f"{uid}_a" if uid else None),
                }
                if grp:
                    params["group_id"] = grp.id
                msg_svc.create_message(db, **params)
                created += 1

        return created

    # Parse and dispatch to the appropriate importer
    try:
        headers, data_rows = _parse_xlsx(file)
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Processing xlsx requires 'openpyxl' package. Install it to enable xlsx support.",
        )

    if excel_type == ExcelType.LINE_MESSAGE:
        created = _import_line_messages(db, msg_svc, grp, headers, data_rows)
    elif excel_type == ExcelType.QA_MESSAGE:
        created = _import_qa_messages(db, msg_svc, grp, headers, data_rows)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported excel_type: {excel_type.value}",
        )

    db.commit()

    return {
        "status": "success",
        "message": f"Imported {created} records for type {excel_type.value}",
        "group": {"id": grp.id, "uniid": grp.uniid, "name": grp.name} if grp else None,
    }
