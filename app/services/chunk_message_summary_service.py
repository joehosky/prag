from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from fastapi import BackgroundTasks

from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
from app.models.chunk_message_summary import ChunkMessageSummary
from app.services.bm25_service import (
    index_chunks_for_date_range_background,
    BM25Service,
)
from app.repositories.group_repo import GroupRepository
from app.repositories.message_repo import MessageRepository
from app.agents.llm_manager import get_llm_manager
import json
from app.utils.batching import chunk_list
from app.utils.text_chunker import split_text_to_chunks
from app.db.session import SessionLocal
from app.services.embedding_service import generate_embedding
from app.vector_store.qdrant_client import QdrantService
import uuid
import logging
from datetime import datetime, time as dt_time, timedelta, timezone

logger = logging.getLogger(__name__)


class ChunkMessageSummaryService:
    def __init__(self, repo: Optional[ChunkMessageSummaryRepository] = None) -> None:
        self.repo = repo or ChunkMessageSummaryRepository()

    def create_summary(
        self, db: Session, *, chunk_id: str, group_id: int, **kwargs
    ) -> ChunkMessageSummary:
        payload: Dict[str, Any] = {"chunk_id": chunk_id, "group_id": group_id}
        payload.update(kwargs)
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[ChunkMessageSummary]:
        return self.repo.get(db, id)

    def get_by_chunk_id(
        self, db: Session, chunk_id: str
    ) -> Optional[ChunkMessageSummary]:
        return self.repo.get_by_chunk_id(db, chunk_id)

    def list_by_group(
        self, db: Session, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChunkMessageSummary]:
        return self.repo.list_by_group(db, group_id, skip=skip, limit=limit)

    def list_by_time_range(
        self, db: Session, group_id: int, start_time, end_time
    ) -> List[ChunkMessageSummary]:
        return self.repo.list_by_time_range(db, group_id, start_time, end_time)

    def update_summary(
        self, db: Session, db_obj: ChunkMessageSummary, updates: Dict[str, Any]
    ) -> ChunkMessageSummary:
        return self.repo.update(db, db_obj, updates)

    def get_by_qdrant_point_id(
        self, db: Session, point_id: str
    ) -> Optional[ChunkMessageSummary]:
        return self.repo.get_by_qdrant_point_id(db, point_id)

    def schedule_bm25_index(
        self,
        background_tasks: BackgroundTasks,
        group_id: int,
        start_date: str,
        end_date: str,
    ) -> None:
        """Schedule BM25 indexing as a background task.

        This method is a small convenience wrapper so routers/controllers can
        call it with FastAPI's `BackgroundTasks` instance.
        """
        background_tasks.add_task(
            index_chunks_for_date_range_background, group_id, start_date, end_date
        )


def _parse_datetime(value: str) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.strptime(value, "%Y-%m-%d")


def summarize_group_messages_background(
    group_id: int, start_date: str, end_date: str
) -> None:
    """Background task to summarize messages for a group in the date range.

    This function creates its own DB session and performs the orchestration:
    - fetch messages
    - group by day
    - batch into units of 20 messages
    - call LLM per unit
    - create ChunkMessageSummary records
    - (placeholder) split message content for embedding/Qdrant
    - schedule BM25 indexing
    """
    db = SessionLocal()
    try:
        sdt = datetime.combine(_parse_datetime(start_date).date(), dt_time.min)
        edt = datetime.combine(
            _parse_datetime(end_date).date(), dt_time(23, 59, 59, 999000)
        )

        msg_repo = MessageRepository()
        grp_repo = GroupRepository()
        chunk_repo = ChunkMessageSummaryRepository()

        # fetch messages in range
        messages = msg_repo.list_by_time_range(db, group_id, sdt, edt)
        if not messages:
            logger.info(
                "No messages found for group %s in range %s - %s",
                group_id,
                start_date,
                end_date,
            )
            return

        # group messages by calendar day (based on message_time)
        days = {}
        for m in messages:
            if not m.message_time:
                continue
            day = m.message_time.date()
            days.setdefault(day, []).append(m)

        # get system prompt
        core_rules = """=== Key Rules ===
                        1. Each topic MUST be an independent JSON element (do NOT merge into a summary)
                        2. Identify up to 15 different topics
                        3. Each topic should only contain related message ids
                        4. Messages of the same topic may not be consecutive; group them correctly

                        === Topic Classification Standards ===
                        - Same event/same discussion thread = same topic
                        - Different matters/topics = different topics
                        - Example topics: "Appointment scheduling", "Data delivery", "Expense reimbursement", "Problem discussion", etc.

                        === Output Requirements ===
                        - MUST output a JSON array with one element per topic
                        - detail: A long, detailed explanation in Chinese, preserving all key information from the original messages
                        - ids: Array of message ids belonging to this topic
                        - startTime/endTime: Time range of this topic
                        """

        # 組合 base_prompt
        grp = grp_repo.get(db, group_id)
        if grp and grp.chunk_summary_prompt:
            # 有自訂 prompt：保留原有 + 加上核心規則
            base_prompt = (
                grp.chunk_summary_prompt
                + "\n\nClassify chat messages by topic.\n\n"
                + core_rules
            )
        else:
            # 無自訂 prompt：使用預設任務描述 + 核心規則
            base_prompt = "Your task: Classify chat messages by topic.\n\n" + core_rules

        # input/output spec
        input_spec = '[{"id": 123, "time": "15:04:05", "user": "Alice", "content": "Message content"}]'

        output_spec = """[
        {"detail": "A long, detailed explanation in Chinese about topic 1, preserving all key information from the original messages", "ids": [123, 124, 125], "startTime": "10:05:00", "endTime": "10:15:00"},
        {"detail": "A long, detailed explanation in Chinese about topic 2, preserving all key information from the original messages", "ids": [126, 130, 135], "startTime": "11:20:00", "endTime": "11:45:00"},
        {"detail": "A long, detailed explanation in Chinese about topic 3, preserving all key information from the original messages", "ids": [140, 141], "startTime": "14:10:00", "endTime": "14:20:00"}
        ]"""

        total = 0
        for day, msgs in days.items():
            day_start = datetime.combine(day, dt_time.min)
            day_end = datetime.combine(day, dt_time(23, 59, 59, 999000))

            # split into units of up to 20 messages
            objs = msgs
            units = list(chunk_list(objs, 20))

            all_topics = []
            for unit in units:
                snippets = []
                for mm in unit:
                    time_str = (
                        mm.message_time.strftime("%H:%M:%S")
                        if mm.message_time
                        else "00:00:00"
                    )
                    user = mm.user_name or mm.user_uid or ""
                    content = mm.message_content or mm.link_description or ""
                    snippets.append(
                        {
                            "id": mm.id,
                            "time": time_str,
                            "user": user,
                            "content": content,
                        }
                    )

                # construct prompt (include input/output spec)
                prompt = f"""{base_prompt}
                        === 輸入格式(JSON) ===
                        {input_spec}

                        === 輸出格式(JSON) ===
                        {output_spec}

                        === 重要提醒 ===
                        ❌ 錯誤示範：輸出一個元素包含所有內容的總結
                        ✅ 正確示範：輸出多個元素，每個元素代表一個獨立主題

                        請將訊息依主題拆分，輸出純 JSON 陣列（不要 markdown 標記）。
                        回應內容使用繁體中文描述。"""

                try:
                    snippets_json = (
                        json.dumps(snippets, ensure_ascii=False)
                        if snippets is not None
                        else ""
                    )

                    llm_manager = get_llm_manager()
                    try:
                        raw = llm_manager.invoke(
                            snippets_json, prompt, max_tokens=12000
                        )
                    except Exception as e:
                        logger.exception("LLM call failed: %s", e)
                        raise

                    batch_topics = []
                    try:
                        if raw:
                            raw_str = raw.strip()
                            if raw_str.startswith("```"):
                                raw_str = raw_str.split("```")[1]
                                if raw_str.startswith("json"):
                                    raw_str = raw_str[4:]
                                raw_str = raw_str.strip()
                            else:
                                raw_str = raw_str

                            parsed = json.loads(raw_str)
                            if isinstance(parsed, list):
                                batch_topics = parsed
                            elif isinstance(parsed, dict):
                                for v in parsed.values():
                                    if isinstance(v, list):
                                        batch_topics = v
                                        break
                    except Exception:
                        logger.debug("parse_llm_topics: failed to parse as JSON")

                    all_topics.extend(batch_topics)
                except Exception:
                    logger.exception(
                        "LLM error when summarizing group %s day %s", group_id, day
                    )
                    continue

            # if no topics, mark as done (TODO: update MessageSummaryTag if exists)
            if len(all_topics) == 0:
                logger.info("No topics returned for group %s day %s", group_id, day)
                continue

            # build id->content map
            id_to_content = {
                o.id: f"[{o.message_time.strftime('%H:%M:%S')}] {o.user_name or o.user_uid}: {o.message_content or o.link_description or ''}"
                for o in objs
            }

            # delete old summaries for the same day
            old = chunk_repo.find_by_group_and_day(db, group_id, day_start, day_end)
            qdrant_ids = [o.qdrant_point_id for o in old if o.qdrant_point_id]
            chunk_ids = [o.chunk_id for o in old if o.chunk_id]
            try:
                if qdrant_ids:
                    QdrantService().delete_points(qdrant_ids)
            except Exception:
                logger.exception(
                    "Failed to delete old qdrant points for group %s day %s",
                    group_id,
                    day,
                )

            # delete DB rows
            chunk_repo.delete_by_group_and_day(db, group_id, day_start, day_end)
            db.commit()

            # remove old docs from BM25 index (best-effort) so reindex starts clean
            try:
                if chunk_ids:
                    bm25 = BM25Service()
                    for cid in chunk_ids:
                        try:
                            bm25.delete_chunk(cid)
                        except Exception:
                            logger.exception("BM25: failed to delete old doc %s", cid)
            except Exception:
                logger.exception(
                    "BM25: unexpected error while cleaning old docs for group %s day %s",
                    group_id,
                    day,
                )

            # create new summaries
            success_all = True
            for t in all_topics:
                try:
                    ids_list = t.get("ids", [])
                    ids_str = (
                        ",".join(str(int(i)) for i in ids_list) if ids_list else ""
                    )
                    desc = t.get("detail", "")

                    msg_parts = [id_to_content.get(int(i), "") for i in ids_list]
                    msg_content = "\n".join([p for p in msg_parts if p])

                    new_chunk_id = str(uuid.uuid4())
                    payload = {
                        "chunk_id": new_chunk_id,
                        "group_id": group_id,
                        "start_time": day_start,
                        "end_time": day_end,
                        "message_ids": ids_str,
                        "message_summary": desc,
                        "message_content": msg_content,
                    }
                    item = chunk_repo.create_summary(db, payload)
                    db.commit()
                    db.refresh(item)

                    # prepare for embedding / qdrant: split message_content into chunks
                    if item.message_content:
                        text_chunks = split_text_to_chunks(
                            item.message_content, max_chars=4096
                        )
                        # generate embeddings for each text chunk and upsert to Qdrant
                        points = []
                        for i, txt in enumerate(text_chunks):
                            try:
                                vec = generate_embedding(txt, timeout=60, retries=1)
                            except Exception:
                                logger.exception(
                                    "Embedding generation failed for summary %s chunk %d",
                                    item.id,
                                    i,
                                )
                                # skip this chunk
                                continue

                            pid = str(uuid.uuid4())
                            tz = timezone(timedelta(hours=8))
                            date_str = day_start.date().isoformat()
                            start_iso = day_start.replace(tzinfo=tz).isoformat()
                            end_iso = day_end.replace(tzinfo=tz).isoformat()
                            created_iso = datetime.now(tz).isoformat()

                            payload_meta = {
                                "created_at": created_iso,
                                "date": date_str,
                                "end_time": end_iso,
                                "group_id": group_id,
                                "start_time": start_iso,
                                "summary_id": item.id,
                                "chunk_id": item.chunk_id,
                            }
                            points.append(
                                {"id": pid, "vector": vec, "payload": payload_meta}
                            )

                        if points:
                            try:
                                QdrantService().add_points(points)
                                # store first point id and embedding vector on the summary
                                first = points[0]
                                try:
                                    item.qdrant_point_id = first["id"]
                                    item.embedding = first["vector"]
                                    db.add(item)
                                    db.commit()
                                except Exception:
                                    logger.exception(
                                        "Failed to persist qdrant id/embedding for summary %s",
                                        item.id,
                                    )
                            except Exception:
                                logger.exception(
                                    "Failed to upsert points to Qdrant for summary %s",
                                    item.id,
                                )
                        else:
                            logger.info(
                                "Prepared %d text chunks for summary id %s (no points to upsert)",
                                len(text_chunks),
                                item.id,
                            )
                except Exception:
                    logger.exception(
                        "Failed to create chunk summary for group %s day %s",
                        group_id,
                        day,
                    )
                    success_all = False

            # schedule BM25 indexing for this day range
            try:
                # schedule background BM25 task (fire-and-forget)
                index_chunks_for_date_range_background(
                    group_id, day_start.isoformat(), day_end.isoformat()
                )
            except Exception:
                logger.exception(
                    "Failed to schedule BM25 for group %s day %s", group_id, day
                )

            total += len(all_topics)

        logger.info(
            "Summary job finished for group %s range %s-%s total topics %d",
            group_id,
            start_date,
            end_date,
            total,
        )
    finally:
        db.close()
