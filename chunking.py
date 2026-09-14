def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> list[str]:

    if not text.strip():
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks