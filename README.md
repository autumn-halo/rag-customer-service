# RAG 电商知识库问答系统

> 基于 LangChain 的企业级 RAG 知识库问答系统：面向电商商品咨询场景，单机可跑、Docker 可部署。
> 支持多用户多会话、流式回答、知识库引用溯源、混合检索 + 重排。

> ⚙️ 开发中：当前处于阶段 1（项目地基）。功能清单与架构图将在后续阶段补齐。

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
