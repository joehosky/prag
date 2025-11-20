from app.db.session import SessionLocal
from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
import json

ids = [58, 62, 64, 59, 67, 66]

db = SessionLocal()
repo = ChunkMessageSummaryRepository()
try:
    out = {}
    for cid in ids:
        ch = repo.get(db, cid)
        if not ch:
            out[cid] = None
            continue
        out[cid] = {
            "id": ch.id,
            "chunk_id": getattr(ch, "chunk_id", None),
            "message_summary": getattr(ch, "message_summary", None),
            "message_content": getattr(ch, "message_content", None),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
finally:
    db.close()
