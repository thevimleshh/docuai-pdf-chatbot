import chromadb


client = chromadb.PersistentClient(
    path="chroma_db"
)


collection = client.get_or_create_collection(
    name="documents"
)


def add_chunks(chunks, document_id):

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "document_id": document_id
        }
        for _ in chunks
    ]

    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )

    return len(chunks)


def search_chunks(
    question,
    document_id,
    n_results=3
):

    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        where={
            "document_id": document_id
        }
    )

    return results["documents"][0]