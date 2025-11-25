"""Test BM25 cache performance"""

import time
from app.services.bm25_service import get_bm25_service


def test_bm25_cache():
    group_id = 1
    query = "廖萬全 同意書 簽署"

    print("=" * 60)
    print("BM25 Cache Performance Test")
    print("=" * 60)

    # Test 1: First call (cold)
    print("\n📊 Test 1: First call (cold start)")
    bm25 = get_bm25_service()
    print(f"  Total docs in index: {len(bm25.docs)}")

    start = time.time()
    results = bm25.search(query, top_k=50, group_id=group_id)
    elapsed = time.time() - start
    print(f"  ✅ Search completed in {elapsed:.3f}s")
    print(f"  Results: {len(results)} documents")

    # Test 2: Second call (should use cache)
    print("\n📊 Test 2: Second call (cache hit)")
    start = time.time()
    results = bm25.search(query, top_k=50, group_id=group_id)
    elapsed = time.time() - start
    print(f"  ✅ Search completed in {elapsed:.3f}s")
    print(f"  Results: {len(results)} documents")

    # Test 3: Third call (cache hit)
    print("\n📊 Test 3: Third call (cache hit)")
    start = time.time()
    results = bm25.search(query, top_k=50, group_id=group_id)
    elapsed = time.time() - start
    print(f"  ✅ Search completed in {elapsed:.3f}s")
    print(f"  Results: {len(results)} documents")

    # Check cache status
    print("\n📈 Cache Status:")
    print(f"  Cached groups: {list(bm25._group_caches.keys())}")
    print(f"  Group {group_id} cached: {group_id in bm25._group_caches}")

    if group_id in bm25._group_caches:
        cache = bm25._group_caches[group_id]
        print(f"  Cached docs for group {group_id}: {len(cache['ids'])}")


if __name__ == "__main__":
    test_bm25_cache()
