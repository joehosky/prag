from app.core.logging import setup_logging
import os
import asyncio
import json

from app.services.query_service import QueryService

setup_logging()
# enable debug injection
os.environ["DEBUG_QUERY_INJECT"] = "1"


async def main():
    svc = QueryService()
    res = await svc.query_group(
        "C2d3216af8f42fb0a039400ece7daa754",
        "包聖嬌案主前測及設備教學回報",
        top_k=10,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
