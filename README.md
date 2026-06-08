# ResearchFlow

ResearchFlow 是一个基于 LLM Agent 的智能研究助手。MVP 目标是跑通：

```text
研究任务输入 -> Agent 自动规划 -> 搜索/阅读/提取 -> RAG 检索 -> 最终 Markdown 报告
```

## 技术栈

- Backend: FastAPI, LangGraph, SQLAlchemy, Alembic
- Database: PostgreSQL + pgvector
- LLM: DeepSeek / Qwen 等 OpenAI-compatible 国内模型，默认 mock
- Search: mock / ddgs 可配置搜索工具
- Reader: trafilatura 网页正文抽取
- Uploads: PDF / Markdown / TXT 本地文档读取
- RAG: PostgreSQL + pgvector chunks 检索
- Memory: 跨任务长期记忆召回与沉淀
- Citations: 报告引用编号和证据追踪
- Frontend: React + Vite

## 推荐部署方式

推荐不用 Docker，直接部署到服务器：

```text
Nginx
  ├─ /      -> React/Vite dist
  └─ /api   -> FastAPI backend
                  ↓
             PostgreSQL + pgvector
```

完整服务器部署文档见 [docs/deploy-server.md](docs/deploy-server.md)。

## 本地启动

### 1. 准备 PostgreSQL

先创建数据库和用户，并启用 pgvector：

```sql
CREATE DATABASE researchflow;
CREATE USER researchflow WITH PASSWORD 'researchflow';
GRANT ALL PRIVILEGES ON DATABASE researchflow TO researchflow;
\c researchflow
CREATE EXTENSION IF NOT EXISTS vector;
```

Windows 原生安装说明见 [docs/local-postgres-windows.md](docs/local-postgres-windows.md)。

### 2. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
Copy-Item .env.example .env
alembic upgrade head
python scripts/check_database.py
uvicorn app.main:app --reload
```

默认 `.env.example` 使用 mock LLM、mock Search 和 mock Embedding，方便先跑通流程。

如果要打开真实搜索：

```env
SEARCH_PROVIDER=ddgs
SEARCH_MAX_RESULTS=5
SEARCH_REGION=wt-wt
```

如果要接国内 LLM：

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
```

RAG 默认使用 deterministic mock embedding：

```env
EMBEDDING_PROVIDER=mock
EMBEDDING_DIMENSIONS=384
CHUNK_MAX_CHARS=900
CHUNK_OVERLAP_CHARS=120
RAG_TOP_K=5
```

### 3. 启动前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

访问：

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health

### 4. 本地完整联调

在 PostgreSQL 已安装并运行、`.env` 已配置后，可以运行：

```powershell
.\scripts\local-integration.ps1
```

这个脚本会依次执行：

- 检查后端导入
- 执行 `alembic upgrade head`
- 检查 pgvector 和关键表
- 启动后端 API，如果当前没有运行
- 创建一个研究任务并跑完整 Agent 流程
- 检查 `steps / sources / report / citations / memories`

如果脚本在数据库阶段失败，优先检查：

- PostgreSQL 是否正在监听 `localhost:5432`
- `backend/.env` 里的 `DATABASE_URL` 是否正确
- 数据库里是否已执行 `CREATE EXTENSION IF NOT EXISTS vector;`

## 当前 MVP 能力

- 任务创建 API
- LangGraph 研究流程
- Agent 执行日志
- ddgs 搜索工具
- trafilatura 网页正文读取
- PDF / Markdown / TXT 上传和解析
- PostgreSQL + pgvector 文档 chunks 入库和检索
- 长期记忆写入与检索
- 报告引用编号和 evidence chunks 落库
- React 研究工作台：执行流、来源、引用证据、长期记忆和报告预览

下一步会继续补记忆去重、可信度评分和 LLM 结构化信息抽取。
