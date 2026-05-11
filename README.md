# FitChef — 健身饮食 AI 问答平台

基于 RAG（检索增强生成）的健身饮食知识库问答系统。用户用自然语言提问，系统从营养知识库中检索相关文档，结合 DeepSeek 大模型生成带来源引用的专业回答。

## 功能特性

- **自然语言问答**：支持流式输出，回答逐字展示，体验流畅
- **知识库检索**：涵盖食材营养成分、菜谱、膳食指南三大类文档
- **智能拦截**：自动识别与健身饮食无关的问题并拒绝回答
- **对话记忆**：跨轮次理解上下文，支持多轮追问
- **检索质量可量化**：内置 55 题评测集，Hit Rate + MRR 双指标
- **全链路可观测**：LangFuse 追踪每次 RAG 调用的各阶段耗时和输入输出

## 系统架构

```
┌──────────┐     SSE 流式 (POST /chat/rag)    ┌──────────────────┐
│  Vue 3   │ ────────────────────────────────> │  FastAPI (8000)   │
│  前端     │ <── query_rewrite, sources,      │  JWT 鉴权         │
│  :5173   │     search_results, tokens...     │  日志中间件        │
└──────────┘                                   └───────┬──────────┘
                                                       │
                                         ┌─────────────┴───────────┐
                                         │      RAG 检索链路        │
                                         │  查询改写 → 话题拦截     │
                                         │  → 混合检索 → 重排序     │
                                         │  → LLM 生成             │
                                         └─────────────┬───────────┘
                                                       │
                              ┌────────────────────────┴──────┐
                              │  MySQL (用户/会话/消息)        │
                              │  Milvus (向量存储与检索)       │
                              │  Ollama (bge-m3 embedding)    │
                              │  DeepSeek API (LLM 生成)      │
                              │  LangFuse (可观测追踪)         │
                              └───────────────────────────────┘
```

RAG 检索分为两条路线并行执行：
- **BM25 路线**：查询改写输出的 `keywords` → jieba 分词 → BM25 关键词匹配
- **向量路线**：查询改写输出的 `semantic` → Ollama bge-m3 embedding → Milvus 向量检索
- 两条路线的结果通过 **RRF（倒数排名融合）** 算法合并，再用 **Cross-Encoder 重排序** 精排，最终取 Top-K 文档送入 LLM 生成回答

## 快速开始

### 前置条件

1. 安装 **Docker Desktop**
2. 安装 **Ollama** 并拉取 embedding 模型：
   ```bash
   ollama pull bge-m3
   ```
3. 准备 **DeepSeek API Key**（[申请地址](https://platform.deepseek.com)）

### 部署步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd my_project1

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY

# 3. 一键启动全部服务
docker compose up -d

# 4. 访问前端页面
# http://localhost:5173
```

首次启动会自动拉取镜像、构建后端和前端、初始化数据库表、加载知识库并生成向量索引，可能需要几分钟。后续启动直接 `docker compose up -d` 即可，秒级就绪。

## 服务列表

执行 `docker compose up -d` 后共启动 8 个容器：

| 容器名 | 服务 | 端口 | 说明 |
|--------|------|------|------|
| fitchef-frontend | Vue 3 前端 | 5173 | Web 对话界面 |
| fitchef-backend | FastAPI 后端 | 8000 | API + RAG 完整链路 |
| fitchef-mysql | MySQL 8.0 | 3306 | 用户/会话/消息持久化 |
| fitchef-milvus | Milvus 2.5 | 19530 | 向量存储与相似度检索 |
| fitchef-etcd | etcd 3.5 | 2379 | Milvus 元数据协调 |
| fitchef-minio | MinIO | 9000 | Milvus 对象存储 |
| fitchef-langfuse | LangFuse | 3000 | LLM 可观测性平台 |
| fitchef-langfuse-db | PostgreSQL 16 | 5432 | LangFuse 数据存储 |

## 环境变量说明 (.env)

### 必填

| 变量 | 说明 | 示例 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` |

### LLM 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1/` | API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |

### Embedding 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama 地址（容器内必须用此写法） |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | Embedding 模型 |

### 数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` | `mysql` | 容器内用服务名 |
| `DB_PORT` | `3306` | |
| `DB_USER` | `root` | |
| `DB_PASSWORD` | `123456` | |
| `DB_NAME` | `my_project1` | |

### Milvus 向量数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MILVUS_HOST` | `milvus` | 容器内用服务名 |
| `MILVUS_PORT` | `19530` | |
| `MILVUS_COLLECTION` | `fitchef_knowledge` | 向量集合名称 |

### JWT

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | — | 生产环境务必更换 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token 有效期（24小时） |

### LangFuse 可观测（可选）

| 变量 | 说明 |
|------|------|
| `LANGFUSE_PUBLIC_KEY` | 公钥，不配则自动禁用追踪 |
| `LANGFUSE_SECRET_KEY` | 密钥 |
| `LANGFUSE_HOST` | 默认 `http://langfuse:3000` |

### RAG 参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_TOP_K` | `5` | 最终送入 LLM 的文档数 |
| `RAG_USE_RERANK` | `True` | 是否启用 Cross-Encoder 重排序 |
| `RAG_USE_QUERY_REWRITE` | `True` | 是否启用 LLM 查询改写 |

## 容器间通信注意事项

**不要写 localhost。** 容器内部 localhost 指向容器自己，不是宿主机也不是其他容器。

- 服务间调用用 **Docker 服务名**：后端连 MySQL 写 `DB_HOST=mysql`，连 Milvus 写 `MILVUS_HOST=milvus`
- 访问宿主机 Ollama 必须用 `host.docker.internal:11434`（已在 `docker-compose.yml` 配置 `extra_hosts`）
- Vite 开发代理目标写 `backend:8000`，而不是 `localhost:8000`

## 常用命令

```bash
# 服务管理
docker compose up -d                       # 启动全部
docker compose down                        # 停止全部
docker compose restart backend             # 重启单个服务
docker compose up -d --build backend       # 重建后端（改了代码时用）
docker compose up -d --build frontend      # 重建前端

# 日志查看
docker compose logs -f backend             # 后端日志（实时）
docker compose logs -f frontend            # 前端日志（实时）
docker compose logs --tail=50 backend      # 最近 50 行

# 进入容器调试
docker exec -it fitchef-backend bash       # 进入后端容器
docker exec -it fitchef-mysql mysql -uroot -p123456  # 进入 MySQL

# 清理重建（重大问题排查时用）
docker compose down -v                     # 停止并删除数据卷
docker compose up -d --build               # 重新构建启动
```

## API 接口

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/auth/register` | 用户注册 | 无 |
| POST | `/auth/login` | 用户登录，返回 JWT | 无 |
| GET | `/auth/me` | 获取当前用户信息 | Bearer Token |
| POST | `/chat/rag` | **RAG 流式对话**（SSE） | Bearer Token |
| GET | `/chat/conversations` | 获取会话列表 | Bearer Token |
| GET | `/chat/conversations/{id}/messages` | 获取会话消息 | Bearer Token |
| DELETE | `/chat/conversations/{id}` | 删除会话 | Bearer Token |
| POST | `/chat/eval` | 运行检索评测 | Bearer Token |

后端启动后可通过 Swagger 文档浏览和测试所有接口：`http://localhost:8000/docs`

## 项目结构

```
my_project1/
├── docker-compose.yml        # 全栈 Docker 编排
├── Dockerfile.backend        # 后端镜像构建
├── Dockerfile.frontend       # 前端镜像构建
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── main.py                   # FastAPI 应用入口
├── run.py                    # 开发模式启动脚本
├── README.md
│
├── app/
│   ├── core/                 # 基础设施
│   │   ├── config.py           Pydantic 配置中心
│   │   ├── database.py         异步 SQLAlchemy 引擎
│   │   ├── security.py         JWT 创建/验证
│   │   ├── middleware.py       HTTP 日志中间件
│   │   ├── logger.py           Loguru 日志
│   │   └── hashing.py          bcrypt 密码哈希
│   │
│   ├── models/               # ORM 数据库模型
│   │   ├── user.py             users 表
│   │   ├── conversation.py     conversations 表
│   │   └── message.py          messages 表
│   │
│   ├── schemas/              # Pydantic 请求/响应校验
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   │   └── conversation.py
│   │
│   ├── routers/              # HTTP 路由
│   │   ├── auth.py             /auth/*
│   │   └── chat.py             /chat/*
│   │
│   ├── services/             # 业务逻辑
│   │   ├── rag_chat_service.py         RAG 全链路编排（核心）
│   │   ├── query_rewriter_service.py   查询改写
│   │   ├── hybrid_search_service.py    混合检索（BM25 + 向量 → RRF）
│   │   ├── bm25_service.py             BM25 关键词检索
│   │   ├── embedding_service.py        Ollama embedding + Milvus
│   │   ├── reranker_service.py         Cross-Encoder 重排序
│   │   ├── conversation_service.py     会话管理 + 摘要生成
│   │   ├── user_service.py             用户注册/登录
│   │   ├── observability.py            LangFuse 追踪
│   │   ├── eval_service.py             检索质量评测
│   │   └── fitchef_loader.py           知识库文档加载
│   │
│   ├── data/                 # 知识库原始数据
│   │   ├── china_food_composition.json  食物成分表
│   │   ├── recipes_64k.csv              食谱数据
│   │   ├── cuisines.csv                 菜系数据
│   │   └── dietary_guidelines.md        膳食指南
│   │
│   └── indexes/              # 向量索引持久化（运行时生成）
│
└── frontend/
    ├── vite.config.js         # Vite 配置（代理后端）
    └── src/
        ├── services/api.js         API 调用 + SSE 流式处理
        └── components/
            ├── LoginForm.vue        登录/注册
            ├── ChatLayout.vue       主布局
            ├── Sidebar.vue          会话列表
            ├── ChatArea.vue         聊天区域 + 流式渲染
            ├── MessageBubble.vue    消息气泡
            └── StatsBadge.vue       知识库统计
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 (Composition API) | |
| 构建工具 | Vite 8 | |
| 样式 | 纯 CSS | 无第三方 UI 框架 |
| 后端框架 | FastAPI | 异步，自动生成 API 文档 |
| ORM | SQLAlchemy 2.0（异步） | aiomysql 驱动 |
| 向量数据库 | Milvus 2.5 | pymilvus 客户端 |
| 关键词检索 | rank-bm25 + jieba | BM25 中文分词 |
| 重排序 | SentenceTransformers | bge-reranker-v2-m3 |
| LLM | DeepSeek API | OpenAI SDK 兼容调用 |
| Embedding | Ollama bge-m3 | 本地 1024 维向量 |
| 可观测 | LangFuse | 全链路耗时/输入输出追踪 |
| 日志 | Loguru | 控制台 + 文件滚动输出 |
| 鉴权 | JWT (python-jose) | 24 小时有效期 |
| 密码 | bcrypt | |
| 部署 | Docker Compose | 8 容器一键启动 |

## LangFuse 可观测

项目启动后访问 `http://localhost:3000` 进入 LangFuse 控制台，可以查看每次 RAG 调用的完整追踪链路：

- 查询改写耗时
- 混合检索（BM25 + 向量）耗时
- 重排序耗时
- LLM 生成耗时
- 各阶段的输入输出内容

如果没有配置 LangFuse 密钥，追踪功能会自动禁用，不影响正常使用。

## 检索评测

项目内置 55 道测试题，覆盖食材查询、食谱做法、营养知识三类场景。

```bash
# 通过 API 触发评测
curl -X POST http://localhost:8000/chat/eval \
  -H "Authorization: Bearer <your-token>"
```

评测输出三种检索策略的对比：纯 BM25、纯向量、混合检索，指标为 Hit Rate 和 MRR。

## 故障排查

| 问题 | 检查方向 |
|------|----------|
| 前端页面打不开 | `docker compose ps` 确认各容器状态，特别是 frontend 和 backend |
| 回答不相关 | 检查 `query_rewrite` SSE 事件，查看改写后的关键词是否正确 |
| Ollama 连接失败 | 确认 Ollama 在宿主机运行，`.env` 中 `OLLAMA_BASE_URL` 是 `http://host.docker.internal:11434` |
| Milvus 连接失败 | 检查 etcd 和 minio 容器是否正常运行 |
| 后端启动报错 | `docker compose logs backend` 查看具体错误，常见于 .env 缺失 API Key |
| 端口冲突 | 本机是否有其他服务占用了 3306/8000/5173 等端口 |
