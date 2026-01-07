"""
RAG Engine — ChromaDB + OpenAI Embeddings
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI

from config import OPENAI_API_KEY, DATA_DIR

# Директория для ChromaDB
CHROMA_DIR = DATA_DIR / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# OpenAI client для эмбеддингов
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False)
)


def get_collection(user_id: int):
    """Получить или создать коллекцию для пользователя"""
    collection_name = f"user_{user_id}"
    return chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def get_embedding(text: str) -> List[float]:
    """Получить эмбеддинг через OpenAI"""
    if not openai_client:
        return []
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]  # Лимит токенов
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[RAG] Embedding error: {e}")
        return []


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Разбить текст на чанки"""
    if not text or len(text) < 100:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Ищем конец предложения или абзаца
        if end < len(text):
            # Ищем точку, перенос строки или конец абзаца
            for sep in ['\n\n', '\n', '. ', '! ', '? ']:
                pos = text.rfind(sep, start + chunk_size // 2, end + 100)
                if pos > start:
                    end = pos + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start < 0:
            start = 0
    
    return chunks


def add_document(
    user_id: int,
    property_id: int,
    property_name: str,
    file_name: str,
    text: str
) -> int:
    """Добавить документ в RAG"""
    
    if not text or len(text) < 50:
        print(f"[RAG] Skip empty document: {file_name}")
        return 0
    
    collection = get_collection(user_id)
    chunks = chunk_text(text)
    
    if not chunks:
        return 0
    
    print(f"[RAG] Adding {len(chunks)} chunks from {file_name}")
    
    ids = []
    embeddings = []
    documents = []
    metadatas = []
    
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        if not embedding:
            continue
        
        chunk_id = f"p{property_id}_f{hash(file_name) % 10000}_{i}"
        
        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(chunk)
        metadatas.append({
            "property_id": property_id,
            "property_name": property_name,
            "file_name": file_name,
            "chunk_index": i
        })
    
    if ids:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"[RAG] Added {len(ids)} chunks to collection user_{user_id}")
    
    return len(ids)


def search(
    user_id: int,
    query: str,
    property_id: Optional[int] = None,
    limit: int = 10
) -> List[Dict]:
    """Поиск релевантных чанков"""
    
    collection = get_collection(user_id)
    
    # Проверяем есть ли документы
    if collection.count() == 0:
        return []
    
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    # Фильтр по property_id если указан
    where_filter = None
    if property_id:
        where_filter = {"property_id": property_id}
    
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print(f"[RAG] Search error: {e}")
        return []
    
    # Форматируем результаты
    chunks = []
    if results and results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            chunks.append({
                "text": doc,
                "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                "distance": results['distances'][0][i] if results['distances'] else 0
            })
    
    return chunks


def delete_property_chunks(user_id: int, property_id: int):
    """Удалить все чанки ЖК"""
    collection = get_collection(user_id)
    
    try:
        # Получаем все ID чанков этого ЖК
        results = collection.get(
            where={"property_id": property_id},
            include=[]
        )
        
        if results and results['ids']:
            collection.delete(ids=results['ids'])
            print(f"[RAG] Deleted {len(results['ids'])} chunks for property {property_id}")
    except Exception as e:
        print(f"[RAG] Delete error: {e}")


def get_stats(user_id: int) -> Dict:
    """Статистика коллекции пользователя"""
    collection = get_collection(user_id)
    return {
        "total_chunks": collection.count(),
        "collection_name": f"user_{user_id}"
    }
