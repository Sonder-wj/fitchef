# FitChef — 健身饮食 AI 问答平台

基于 RAG 的健身饮食知识库问答系统，用自然语言提问（如"鸡胸肉怎么做好吃不柴"），系统从营养知识库中检索相关文档，结合大模型生成带来源引用的专业回答。

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd my_project1

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 一键启动
docker compose up -d

# 4. 访问 http://localhost:5173
```

## 服务架构

| 服务 | 端口 | 说明 |
|------|------|------|
| Vue 3 前端 | 5173 | Web 对话界面 |
| FastAPI 后端 | 8000 | API + RAG 检索链路 |
| MySQL 8.0 | 3306 | 用户/会话/消息存储 |
| Milvus 2.5 | 19530 | 向量检索 |
| LangFuse | 3000 | LLM 可观测追踪 |
| Ollama | 11434 | 本地 embedding（bge-m3） |

## 环境要求

- Docker Desktop
- Ollama 本地安装，并拉取 embedding 模型：`ollama pull bge-m3`
- DeepSeek API Key

## 常用命令

```bash
docker compose down               # 停止全部
docker compose up -d              # 启动全部
docker compose up -d --build backend   # 重建后端
docker compose up -d --build frontend  # 重建前端
docker compose logs -f backend    # 查看后端日志
```

## .env 必填项

```ini
DEEPSEEK_API_KEY=sk-xxx            # 必填
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

其余数据库、Milvus、LangFuse 等已预设默认值，可直接使用。LangFuse 不配密钥则自动禁用。

## 技术栈

**后端：** FastAPI + SQLAlchemy 2.0 + Milvus + LangFuse + SentenceTransformers  
**前端：** Vue 3 (Composition API) + Vite + 纯 CSS  
**LLM：** DeepSeek API + Ollama (bge-m3 embedding)
