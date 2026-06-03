"""
RAG 知识库问答系统 - Streamlit 前端界面
=============================================

启动方式:
    cd /Users/hanser/Desktop/rag-qa-system
    source venv/bin/activate
    streamlit run streamlit_app.py --server.port 8501
"""

import os
import requests
from pathlib import Path
import streamlit as st

# ── 配置 ────────────────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"

# ── 页面设置 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="智能知识库问答系统",
    page_icon="🤖",
    layout="wide",
)

# ── 自定义 CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    .stChatMessage { border-radius: 12px !important; }
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
    .source-tag {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.8rem;
        margin: 2px 4px 2px 0;
    }
    .upload-box {
        border: 2px dashed #1a73e8;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏：文档管理 ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 知识库管理")

    # 显示当前知识库状态
    try:
        resp = requests.get(f"{API_BASE}/api/documents", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            st.metric("已入库文档", len(data.get("documents", [])))
            st.metric("文本片段总数", data.get("total_chunks", 0))
            docs = data.get("documents", [])
        else:
            docs = []
    except Exception:
        st.warning("⚠️ 无法连接后端服务\n请确保 FastAPI 服务已启动 (port 8000)")
        docs = []

    st.divider()

    # 上传文档（使用动态 key 防止重复上传）
    st.subheader("📤 上传文档")

    # 每次上传成功后换 key，Streamlit 会自动清空 uploader
    uploader_key = st.session_state.get("uploader_key", "uploader_v1")

    uploaded_file = st.file_uploader(
        "支持 .md / .txt / .pdf 格式",
        type=["md", "txt", "text", "markdown", "pdf"],
        key=uploader_key,
    )

    if uploaded_file is not None:
        # 用文件大小和名称做去重判断
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded_file") != file_key:
            with st.spinner("正在上传并向量化..."):
                try:
                    mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else "text/plain"
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), mime_type)}
                    resp = requests.post(f"{API_BASE}/api/upload", files=files, timeout=120)
                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(
                            f"✅ 上传成功！\n"
                            f"- 文件名：{result['filename']}\n"
                            f"- 分块数：{result['chunks']}\n"
                            f"- 知识库总块数：{result['total_chunks']}"
                        )
                        # 记录已上传，并换 key 清空 uploader
                        st.session_state["last_uploaded_file"] = file_key
                        st.session_state["uploader_key"] = f"uploader_v{len(st.session_state)}"
                    else:
                        st.error(f"上传失败：{resp.text}")
                except Exception as e:
                    st.error(f"上传出错：{e}")
        else:
            st.caption("ℹ️ 该文件已上传，无需重复操作。")

    st.divider()

    # 已上传文档列表
    if docs:
        st.subheader("📄 已上传文档")
        for doc in docs:
            st.text(f"• {doc}")
    else:
        st.caption("暂无文档，请先上传")

    st.divider()
    st.caption("后端服务需运行在 127.0.0.1:8000")

# ── 主界面：对话区 ──────────────────────────────────────────────────────────
st.title("🤖 智能知识库问答系统")
st.caption("基于 RAG（检索增强生成）技术 · 上传文档后开始提问")

# 初始化对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示对话历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 参考来源"):
                for src in msg["sources"]:
                    st.markdown(f"`{src}`")

# 输入框
if prompt := st.chat_input("向知识库提问..."):
    # 检查知识库是否有内容
    try:
        status_resp = requests.get(f"{API_BASE}/api/documents", timeout=5)
        kb_empty = status_resp.json().get("total_chunks", 0) == 0
    except Exception:
        st.error("无法连接后端服务，请确保 FastAPI 已启动")
        st.stop()

    if kb_empty:
        st.warning("⚠️ 知识库为空，请先在左侧上传文档！")
        st.stop()

    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 API 获取回答
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/ask",
                    json={"question": prompt, "top_k": 4},
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])

                    st.markdown(answer)
                    if sources:
                        with st.expander("📎 参考来源"):
                            for src in sources:
                                st.markdown(f"`{src}`")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    })
                else:
                    err = resp.json().get("detail", resp.text)
                    st.error(f"请求失败：{err}")
            except Exception as e:
                st.error(f"请求出错：{e}")

# ── 清空对话按钮 ────────────────────────────────────────────────────────────
if st.session_state.messages:
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
