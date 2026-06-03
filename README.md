# RAG 知识库问答系统

基于 **ChromaDB + DeepSeek + FastAPI + Streamlit** 构建的检索增强生成（RAG）问答系统。上传文档即可构建专属知识库，支持语义检索与智能问答。

## 技术架构

| 组件 | 选型 | 说明 |
|------|------|------|
| LLM | **DeepSeek** (`deepseek-chat`) | 大模型生成回答 |
| Embedding | **BAAI/bge-m3** (硅基流动) | 文本向量化 |
| 向量数据库 | **ChromaDB** | 本地持久化存储 |
| 后端框架 | **FastAPI** | 高性能异步 API |
| 前端界面 | **Streamlit** | 交互式聊天 UI |

## 核心流程

```
文档上传(.md/.txt) → 文本分块 → Embedding 向量化 → ChromaDB 持久化
                                                          ↓
用户提问           → 转向量检索  → 召回 Top-K 相关片段
                                                          ↓
                   拼接上下文 + Prompt → DeepSeek 生成回答
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/hanserstep/rag-qa-system.git
cd rag-qa-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> **API 获取地址：**
> - DeepSeek: https://platform.deepseek.com/api_keys
> - 硅基流动: https://siliconflow.cn/account/ak

### 4. 启动后端

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 5. 启动前端（可选）

```bash
streamlit run streamlit_app.py --server.port 8501
```

访问 http://localhost:8501 进入对话界面。

## API 接口

### 上传文档

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@技术文档.md"
```

支持格式：`.md` `.txt` `.markdown` `.text`

### 提问

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是 RAG？", "top_k": 4}'
```

返回：

```json
{
  "answer": "RAG（检索增强生成）是一种...",
  "sources": ["技术文档.md - 片段1", "技术文档.md - 片段3"]
}
```

### 查看文档列表

```bash
curl http://localhost:8000/api/documents
```

### 健康检查

```bash
curl http://localhost:8000/api/health
```

## 项目结构

```
rag-qa-system/
├── app.py              # FastAPI 后端服务
├── streamlit_app.py    # Streamlit 前端界面
├── requirements.txt    # Python 依赖
├── .streamlit/         # Streamlit 配置
│   └── config.toml
├── .env.example        # 环境变量模板
└── README.md
```

## 项目亮点

- **完整 RAG 链路**：文档导入 → 文本分块 → 向量检索 → LLM 生成，一条龙实现
- **Prompt 工程**：角色约束 + 上下文注入 + 引用溯源 + 防幻觉策略
- **前后端分离**：FastAPI 提供 RESTful API，Streamlit 提供交互式 UI，可独立部署
- **持久化存储**：ChromaDB 本地存储，重启不丢失知识库数据
- **生产可用**：CORS 跨域支持、错误处理完善、API 文档自动生成

## License

MIT
