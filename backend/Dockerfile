# ============================================================
# 多阶段构建：先构建前端，再打包后端，最终一个容器跑全栈。
# 构建上下文为项目根目录：docker build -f backend/Dockerfile .
# ============================================================

# ---- 阶段 1：构建前端 ----
FROM node:24-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- 阶段 2：后端运行环境 ----
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# 前端构建产物由 FastAPI 托管（static 目录存在时自动启用 SPA 模式）
COPY --from=frontend-build /build/dist ./app/static

EXPOSE 8000

# workers=1 是硬性要求：Chroma 嵌入式模式、BM25 内存索引、
# asyncio 入库队列都要求单进程，多 worker 会互相冲突。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
