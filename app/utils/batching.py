from typing import Iterable, List, TypeVar, Iterator

T = TypeVar("T")


def chunk_list(items: Iterable[T], size: int) -> Iterator[List[T]]:
    """Yield successive chunks of `size` from `items`.

    Example:
        list(chunk_list(range(7), 3)) -> [[0,1,2],[3,4,5],[6]]
    """
    batch: List[T] = []
    for it in items:
        batch.append(it)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
