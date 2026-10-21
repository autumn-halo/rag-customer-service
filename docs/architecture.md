# 架构与设计文档

## 1. 总体架构

三层结构：**前端（Vue3 SPA）→ 后端（FastAPI + LangChain）→ 数据层（SQLite + Chroma + 文件系统）**。
大模型能力（对话/向量化/重排）来自阿里云百炼 DashScope。

```
浏览器 ──HTTP/SSE──▶ FastAPI ──▶ LangChain 编排 ──▶ DashScope(qwen-plus)
                      │  │                              │
                      │  └─▶ 检索层(向量+BM25→RRF→rerank)│
                      │          ├─▶ Chroma(嵌入式)      │
                      │          └─▶ 内存 BM25 索引       │
                      │
                      ├─▶ SQLite（用户/会话/消息/文档/分块）
                      └─▶ 入库队列（asyncio + 线程池）
```

## 2. RAG 问答链路（核心）

```
用户提问
  → 意图分流：商品咨询 or 闲聊？
     ├─ 闲聊 → 自由对话 prompt（不检索）
     └─ 商品咨询：
        1. 双路粗选：向量 top20 + BM25 top20
        2. RRF 融合：score(d) = Σ 1/(60 + rank)
        3. 重排复试：qwen3-rerank top5（失败降级为 RRF 排序）
        4. 兜底判断：无资料 或 最高分 < 0.15 → 固定话术（不调 LLM）
        5. 答案缓存：同问同引用秒回（LRU+TTL，键绑定引用片段集合）
        6. 组装 prompt：客服人设 + 强制 [n] 引用 + 对话历史（最近 3 轮）
        7. qwen-plus 流式生成 → 落库（含引用快照）→ 写缓存
```

## 3. 文档入库链路

```
上传（仅管理员）
  → 保存文件（uuid 命名防路径穿越）+ 建文档记录（pending）
  → 入队（asyncio.Queue，2 worker）
  → 状态 processing
  → 解析（pdf/docx/xlsx/txt/md，中文编码自动探测）
  → 分块（500 字 / 重叠 80，中文分隔符，小段合并防碎片化）
  → 写 chunks 表（事实来源）
  → 批量向量化（每批 25 条，指数退避重试 3 次）→ 写 Chroma
  → 重建 BM25 索引（从 DB 全量）
  → 状态 success / failed（错误信息可读）
```

**崩溃恢复**：启动时把遗留 `processing` 重置为 `pending` 并重新入队；
BM25 索引启动时从 chunks 表全量重建，chunks 表是唯一的"事实来源"。

## 4. SSE 流式协议

```
POST /api/chat/stream   （EventSource 不支持 POST，前端用 fetch + ReadableStream）
→ event: meta   data: {cached, citations:[...], conversation_id}   # 引用先于答案到达
→ event: delta  data: {content}   × N
→ event: done   data: {message_id, token_count}
→ event: error  data: {detail}    # 任何异常都转成 error 事件，绝不 500
（服务端每 15s 心跳防断连；nginx 反代需 proxy_buffering off）
```

引用快照结构：`{index, chunk_id, document_id, document_title, score, content}`——
存进消息表，历史消息重渲染无需再查询，删除文档后历史回答仍完整。

## 5. 数据模型（5 张表）

- **users**：username(唯一) / password_hash(bcrypt) / role(admin|user)
- **conversations**：user_id(FK,索引) / title / 复合索引(user_id, updated_at)
- **messages**：conversation_id(FK,级联删) / role / content / references(JSON 快照) / token_count
- **documents**：filename / stored_path(uuid) / status(索引) / error_message / chunk_count
- **chunks**：document_id(FK,级联删) / chunk_index(唯一约束) / content / meta(JSON) / chroma_id

## 6. 安全设计

- 密码 bcrypt 加盐哈希；JWT 24h 过期；登录失败与用户不存在返回同一提示（防用户枚举）
- 管理员接口双层防护：前端路由守卫 + 后端依赖注入 `require_admin`（403）
- 会话归属校验：他人会话一律 404（不泄露存在性）
- 限流：登录 5 次/分/IP、提问 20 次/分/用户（内存滑动窗口）
- 文件上传：扩展名白名单 + 大小上限 + uuid 存储名防路径穿越
- Markdown 渲染关闭 HTML 注入（XSS 防护）；`.env` 不入库

## 7. 关键设计决策（详见 README ADR）

- Python 3.12（chromadb 与 3.14 不兼容）
- qwen3-rerank 替代已下架的 gte-rerank
- `check_embedding_ctx_length=False`（DashScope 只收原文不收 token 编号）
- 意图分流（关键词路由，小模型分类列入规划）
- 单进程约束：Chroma 嵌入式 / 内存 BM25 / asyncio 队列 → uvicorn `--workers 1`

## 8. 可替换性设计（接口抽象）

| 组件 | 替换路径 |
|---|---|
| 缓存 | 实现 `CacheBackend` 接口 → Redis |
| 重排 | 实现 `Reranker` 接口 → 其他厂商模型 |
| 检索 | `BaseRetriever` 抽象 → Chroma server / Qdrant（语料 >10 万块） |
| 任务队列 | `queue.py` 已隔离 → Celery |
| 数据库 | 改 `DATABASE_URL` → MySQL/PostgreSQL（业务代码零改动） |
| 大模型 | 改 `.env` 的 `MODEL_*` → 任何 OpenAI 兼容模型 |
