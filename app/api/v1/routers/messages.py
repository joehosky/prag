"""
Line Messages Upload / Import Router
"""

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    status,
    BackgroundTasks,
)
from typing import Optional, List
from enum import Enum
from csv import reader as csv_reader

from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.services.group_service import GroupService
from app.services.message_service import MessageService
from app.services.chunk_message_summary_service import (
    summarize_group_messages_background,
)

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
        raise HTTPException(status_code=404, detail="group not found")

    msg_svc = MessageService()

    # Helper: parse workbook into headers + data rows
    async def _parse_xlsx(file_obj):
        import openpyxl
        import tempfile
        import os

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp_path = tmp.name
                while True:
                    chunk = await file_obj.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)

            wb = openpyxl.load_workbook(filename=tmp_path, read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return [], []
            headers = [str(c).strip() if c is not None else "" for c in rows[0]]
            raw_rows = rows[1:]
            data_rows = [
                r
                for r in raw_rows
                if any((c is not None and str(c).strip() != "") for c in r)
            ]
            return headers, data_rows
        finally:
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    # Handler for line_message type
    def _import_line_messages(db, msg_svc, grp, data_rows):
        created = 0

        def _col(row, idx):
            return row[idx] if idx < len(row) else None

        def _parse_dt(val):
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            s = str(val).strip()
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d",
            ):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None

        for row in data_rows:
            # Fixed-column mapping: A..I -> 0..8
            # A: time, B: message_uid, C: reply_message_uid, D: user_name, E: user_uid,
            # F: message_content, G: sticker, H: link_url, I: link_description
            message_time = _parse_dt(_col(row, 0))
            message_uid = _col(row, 1)
            reply_message_uid = _col(row, 2)
            user_name = _col(row, 3)
            user_uid = _col(row, 4)
            message_content = _col(row, 5)
            sticker = _col(row, 6)
            link_url = _col(row, 7)
            link_description = _col(row, 8)

            params = {}
            if grp:
                params["group_id"] = grp.id

            if message_time is not None:
                params["message_time"] = message_time
            if message_uid is not None:
                params["message_uid"] = str(message_uid)
            if reply_message_uid is not None:
                params["reply_message_uid"] = str(reply_message_uid)
            if user_name is not None:
                params["user_name"] = str(user_name)
            if user_uid is not None:
                params["user_uid"] = str(user_uid)
            if message_content is not None:
                params["message_content"] = str(message_content)
            if sticker is not None:
                params["sticker"] = str(sticker)
            if link_url is not None:
                params["link_url"] = str(link_url)
            if link_description is not None:
                params["link_description"] = str(link_description)

            msg_svc.create_message(db, **params)
            created += 1

        return created

    # Handler for qa_message type (imports question/answer pairs)
    def _import_qa_messages(db, msg_svc, grp, data_rows):
        created = 0

        def _col(row, idx):
            return row[idx] if idx < len(row) else None

        import_date = datetime.now().date()
        message_time = datetime.combine(import_date, datetime.min.time())

        for row in data_rows:
            # Expect fixed-column format: A (col 0) = question, B (col 1) = answer
            question = _col(row, 0)
            answer = _col(row, 1)

            parts = []
            if question is not None:
                parts.append(f"question: {question}")
            if answer is not None:
                parts.append(f"answer: {answer}")
            if not parts:
                continue
            message_content = "\n\n".join(parts)

            params = {
                "message_content": str(message_content),
                "message_time": message_time,
            }
            if grp:
                params["group_id"] = grp.id

            msg_svc.create_message(db, **params)
            created += 1

        return created

    # Parse and dispatch to the appropriate importer
    try:
        headers, data_rows = await _parse_xlsx(file)
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Processing xlsx requires 'openpyxl' package. Install it to enable xlsx support.",
        )

    if excel_type == ExcelType.LINE_MESSAGE:
        created = _import_line_messages(db, msg_svc, grp, data_rows)
    elif excel_type == ExcelType.QA_MESSAGE:
        created = _import_qa_messages(db, msg_svc, grp, data_rows)
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


@router.post("/summarize", status_code=202)
async def summarize_messages(
    background_tasks: BackgroundTasks,
    group_uniid: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    """Schedule summarization + embedding + chunking for a group's messages.

    Expects ISO date strings for `start_date` and `end_date`. The task is
    scheduled with FastAPI `BackgroundTasks` and runs `summarize_group_messages_background`.
    """

    gsvc = GroupService()
    grp = gsvc.get_by_uniid(db, group_uniid)
    if not grp:
        raise HTTPException(status_code=404, detail="group not found")

    if not start_date or not end_date:
        raise HTTPException(
            status_code=400, detail="start_date and end_date are required"
        )

    # schedule background work (fire-and-forget)
    background_tasks.add_task(
        summarize_group_messages_background, grp.id, start_date, end_date
    )

    return {
        "status": "accepted",
        "message": "summarization scheduled",
        "group": {"id": grp.id, "uniid": grp.uniid, "name": grp.name},
        "start_date": start_date,
        "end_date": end_date,
    }
