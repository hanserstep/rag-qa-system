# 智能知识库问答系统 (RAG)

基于 LangChain + Chroma + FastAPI 构建的企业知识库智能问答系统，支持多格式文档导入与语义问答。

## 技术栈

| 组件 | 选型 |
|------|------|
| LLM | OpenAI / 国产大模型兼容 |
| 框架 | LangChain |
| 向量库 | Chroma |
| API | FastAPI |
| 文档解析 | PyPDF / Markdown / TXT |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 API Key（支持 OpenAI / 硅基流动 / DeepSeek 等）

# 3. 启动服务
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动后访问 http://localhost:8000/docs 查看 Swagger 文档。

### 上传文档

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@简历.pdf"
```

### 提问

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "这个人的教育背景是什么？"}'
```

### 查看文档列表

```bash
curl http://localhost:8000/api/documents
```

## 架构

```
用户上传文档 → 文本分割 → Embedding 向量化 → Chroma 存储
                                              ↓
用户提问     → Embedding 转向量 → 语义检索相似片段
                                              ↓
              拼接上下文 + Prompt 模板 → LLM 生成回答
```

## 项目亮点

- RAG 全链路实现：文档导入 → 向量化 → 检索 → 生成
- Prompt 工程：角色约束 + 上下文注入 + 引用溯源
- 生产级部署：FastAPI + CORS，支持 API 集成
- 知识库持久化：Chroma 本地存储，重启不丢失
