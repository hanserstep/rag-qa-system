"""
智能知识库问答系统 (RAG)
=========================
基于 ChromaDB + OpenAI SDK 构建的 RAG 问答系统。
支持 TXT/MD/PDF 文档导入、语义检索、多轮对话。

启动方式:
    pip install -r requirements.txt
    cp .env.example .env   # 填入你的 API Key
    uvicorn app:app --reload

API:
    POST /api/upload       # 上传文档（MD/TXT/PDF）
    POST /api/ask          # 提问
    GET  /api/documents    # 查看已导入文档列表
"""

import os
import uuid
import tempfile
import json
import requests
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
import pdfplumber

load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import chromadb
from chromadb.utils import embedding_functions

# ── 配置 ─────────────────────────────────────────────────────────────────────
PERSIST_DIR = os.path.expanduser("~/.rag_chroma_db")
COLLECTION_NAME = "rag_knowledge_base"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

app = FastAPI(title="智能知识库问答系统", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局组件 ─────────────────────────────────────────────────────────────────
# 硅基流动 Embedding
siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY", "")
siliconflow_base_url = "https://api.siliconflow.cn/v1"

# DeepSeek LLM
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
deepseek_base_url = "https://api.deepseek.com/v1"
llm_model = os.getenv("LLM_MODEL", "deepseek-chat")

# ChromaDB
chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)


def get_embedding_function():
    """使用硅基流动的 embedding 模型"""
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=siliconflow_api_key,
        api_base=siliconflow_base_url,
        model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
    )


def get_collection():
    ef = get_embedding_function()
    try:
        return chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
        )
    except Exception:
        return chroma_client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
        )


def extract_pdf_text(file_bytes: bytes) -> str:
    """从 PDF 字节流中提取纯文本（使用 pdfplumber + 临时文件）"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        text_parts = []
        with pdfplumber.open(tmp_path) as pdf:
            print(f"[PDF解析] 共 {len(pdf.pages)} 页", flush=True)
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        result = "\n".join(text_parts)
        print(f"[PDF解析] 提取文本 {len(result)} 字符", flush=True)
        return result
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """简单文本分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
        if start <= 0:
            start = max(start, 1)
    return [c for c in chunks if c.strip()]


def call_deepseek(messages: list) -> str:
    """调用 DeepSeek API"""
    url = f"{deepseek_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": llm_model,
        "messages": messages,
        "temperature": 0.3,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Pydantic 模型 ────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    top_k: int = 4


class AskResponse(BaseModel):
    answer: str
    sources: List[str]


# ── API 路由 ─────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档，支持 MD / TXT / PDF"""
    suffix = Path(file.filename or "default.txt").suffix.lower()
    supported = {".md", ".txt", ".text", ".markdown", ".pdf"}
    if suffix not in supported:
        raise HTTPException(400, f"仅支持 {supported} 格式，当前: {suffix}")

    content = await file.read()
    try:
        if suffix == ".pdf":
            try:
                text = extract_pdf_text(content)
            except Exception as pdf_err:
                raise HTTPException(400, f"PDF 解析失败：{type(pdf_err).__name__}: {pdf_err}")
        else:
            text = content.decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"文件处理失败：{e}")

    if not text.strip():
        raise HTTPException(400, "文档内容为空")

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "文档分块失败")

    collection = get_collection()
    doc_id = str(uuid.uuid4())[:8]

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "source_file": file.filename or "unknown", "chunk_idx": i}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "success": True,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "total_chunks": collection.count(),
    }


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """向知识库提问"""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        raise HTTPException(400, "知识库为空，请先上传文档")

    # 检索
    results = collection.query(
        query_texts=[req.question],
        n_results=min(req.top_k, count),
    )

    context_parts = []
    sources = []
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        context_parts.append(f"[片段{i+1}] {doc}")
        src = meta.get("source_file", "未知")
        sources.append(f"{src} - 片段{i+1}")

    context = "\n\n---\n\n".join(context_parts)

    # 构建 Prompt
    system_prompt = """你是一个智能知识库助手，请基于以下资料片段回答用户问题。
回答要求：
- 严格基于提供的资料，不要编造信息
- 如果资料中没有相关信息，请明确说"根据资料，暂时无法回答此问题"
- 回答末尾标注参考来源（文档名 + 片段编号）
- 使用中文回答

=== 资料片段 ===
{context}

=== 用户问题 ===
{question}

请回答："""

    messages = [
        {"role": "system", "content": system_prompt.format(context=context, question=req.question)},
        {"role": "user", "content": req.question},
    ]

    answer = call_deepseek(messages)
    return AskResponse(answer=answer, sources=sources)


@app.get("/api/documents")
async def list_documents():
    """列出知识库中的文档"""
    try:
        collection = get_collection()
        count = collection.count()
        if count == 0:
            return {"documents": [], "total_chunks": 0}

        all_data = collection.get()
        seen = set()
        docs = []
        for meta in all_data["metadatas"]:
            fid = meta.get("source_file", "unknown")
            if fid not in seen:
                seen.add(fid)
                docs.append(fid)
        return {"documents": docs, "total_chunks": count}
    except Exception:
        return {"documents": [], "total_chunks": 0}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── 启动入口 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
