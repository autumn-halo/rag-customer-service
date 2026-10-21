# RAG 电商知识库问答系统

> 基于 LangChain 的企业级 RAG 知识库问答系统：面向电商商品咨询场景，单机可跑、Docker 可部署。
> 支持多用户多会话、流式回答、知识库引用溯源、混合检索 + 重排。

> ⚙️ 开发中：当前处于阶段 4（RAG 核心已完成）。功能清单与架构图将在后续阶段补齐。

## 设计决策记录（ADR）

| 决策 | 原因 |
|---|---|
| 用 Python 3.12 而非 3.14 | chromadb 依赖的 onnxruntime 无 3.14 的 wheel，且其依赖 pypika 使用了 3.14 已移除的 `ast.Str` |
| 重排模型用 `qwen3-rerank` 而非 `gte-rerank` | 阿里云已下架 gte-rerank 系列，官方推荐 qwen3-rerank（走 compatible-api 通道） |
| 向量化关闭 `check_embedding_ctx_length` | 新版 langchain-openai 默认把文字预分词成 token 编号发送，DashScope 兼容模式只收原始文字（官方推荐非 OpenAI 厂商关闭） |
| BM25 用内存索引而非 SQLite FTS | 避免双检索路径维护成本；chunks 表是事实来源，重启全量重建（10 万块以下毫秒级） |
| 不引 Redis/Celery/Milvus | 单机可跑原则；缓存与队列均以接口抽象隔离，量级增长后可无缝替换 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | Python 3.12 + FastAPI + LangChain |
| 大模型 | 阿里云百炼：qwen-plus / text-embedding-v3 / gte-rerank |
| 向量库 | Chroma（嵌入式） |
| 数据库 | SQLite + SQLAlchemy |

## 快速启动

### 方式一：一键启动（推荐，Windows）

1. 双击项目根目录的 `start.bat`
2. 会自动弹出两个窗口（后端 + 前端），**都别关**
3. 浏览器会自动打开 http://localhost:5173

> 管理员账号：`admin / 123456`
> 注意：bat 脚本内为纯英文（Windows 老式编码下中文会乱码导致解析错乱）

### 方式二：手动命令

```bash
# 1. 配置环境变量
cp .env.example backend/.env   # 然后填入你的 DASHSCOPE_API_KEY

# 2. 后端
cd backend
python -m venv .venv
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000

# 3. 前端
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

## 验证 DashScope Key

```bash
python scripts/check_dashscope.py
```
