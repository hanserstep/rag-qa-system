# 更新日志 (Changelog)

## [Unreleased]

### 新增功能
- 支持 PDF 文档上传（使用 pdfplumber 解析文字版 PDF）
- Streamlit 前端支持 PDF 文件选择

### 修复
- 修复 `app.py` 代码错乱导致后端无法启动的问题
- 修复 Streamlit 前端重复上传同一文件的问题（引入 `session_state` 去重）
- 修复 PDF 解析兼容性问题（改用临时文件方式，替代 `fitz.open(stream=...)`）

### 优化
- 改进错误信息提示，上传失败时显示具体异常原因
- 上传接口增加 MIME 类型自动识别（PDF → `application/pdf`）

---

## [2026-06-03] - 项目初始化

### 新增功能
- 基于 RAG（检索增强生成）架构的智能问答系统
- 支持 `.md` / `.txt` 文档上传与自动切片
- 使用 SiliconFlow `BAAI/bge-m3` Embedding 模型进行文本向量化
- 使用 ChromaDB 实现本地持久化语义检索
- 集成 DeepSeek 大模型作为生成引擎，回答附带原文来源标注
- FastAPI 后端 + Streamlit 前端，前后端分离架构
- 代码开源至 GitHub

### 技术栈
- 后端：FastAPI + ChromaDB + OpenAI SDK
- 前端：Streamlit
- Embedding：SiliconFlow BAAI/bge-m3
- LLM：DeepSeek Chat
