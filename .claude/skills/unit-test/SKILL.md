---
name: unit-test
description: 为当前项目（RAG 电商知识库问答系统）生成单元测试并执行。当用户要求"补测试 / 生成单元测试 / 跑测试 / 测试覆盖率"时使用。
---

# unit-test 技能：为项目生成并执行单元测试

## 项目测试约定（必须遵守）

- 测试目录：`backend/tests/`，按层次组织：
  - `unit/`——纯函数与模块级单元测试
  - `api/`——接口集成测试（httpx TestClient 全链路）
  - `fakes/`——外部依赖的假实现（假模型、假向量化、假重排等）
- `tests/conftest.py` 已提供全局 fixtures，**优先复用，不要重复造**：
  - `client`：测试客户端（自动建临时数据库 + lifespan 播种 admin/123456）
  - `auth_headers` / `admin_headers` / `register_and_login`：快速拿到登录令牌
  - autouse `_fresh_db`：每个测试前自动重建全部表，测试互不影响
- **零 API 消耗原则（硬性）**：测试绝不调用真实 DashScope API。
  需要 LLM / Embedding / Reranker 时，在 `tests/fakes/` 写假实现，
  通过 monkeypatch 注入（参考现有 `fake_llm.py` 和 `test_conversations.py` 的用法）。
- 不要为了迁就测试而修改被测生产代码；外部依赖必须通过接口注入。
- 新测试文件命名 `test_<模块名>.py`。

## 执行流程

1. 扫描 `backend/app/`，找出尚无测试覆盖的模块/函数
   （重点：`core/`、`rag/`、`services/`、`utils/`）。
2. 按上述约定为未覆盖点生成测试：
   - 纯函数 → 直接断言输入输出；
   - 依赖数据库 → 用 `client` fixture，或直接 `SessionLocal()`
     （表已由 `_fresh_db` 建好，指向临时数据库）；
   - 依赖外部 API → 写 fake + monkeypatch 注入。
3. 运行测试（Windows，从 backend 目录执行）：
   ```bash
   cd backend
   .venv/Scripts/python -m pytest -q
   ```
4. 运行代码规范检查：`.venv/Scripts/ruff check .`
5. 失败处理：先定位是测试问题还是生产代码缺陷；若为缺陷则修复生产代码并说明。
6. 汇报结果：新增测试文件与数量、全部测试通过情况、ruff 状态。
   **不自动 git 提交**，除非用户明确要求。

## 覆盖率目标

- 核心模块（`app/core/`、`app/rag/`、`app/services/`）目标 ≥80%。
- 查看覆盖率：
  ```bash
  cd backend
  .venv/Scripts/python -m pytest --cov=app --cov-report=term-missing -q
  ```
