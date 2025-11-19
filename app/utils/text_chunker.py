from typing import List


def split_text_to_chunks(text: str, max_chars: int = 4096) -> List[str]:
    """Split text into chunks of at most `max_chars`, preferring to split on
    newline or space boundaries.

    Trims whitespace at chunk boundaries.
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # try to cut at last newline or space before max_chars
        cut = text.rfind("\n", 0, max_chars)
        if cut == -1:
            cut = text.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        chunk = text[:cut].strip()
        chunks.append(chunk)
        text = text[cut:].strip()

    return chunks
