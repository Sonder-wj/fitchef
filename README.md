# 🥗 FitChef — 健身饮食 AI 问答平台

> **基于 RAG + 意图路由的垂直领域智能问答系统** — 1828 篇饮食知识 + 训练/体测/饮食三模块个人追踪 + 交叉分析,Hit Rate **90.91%**。

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)](https://vuejs.org/)
[![Milvus](https://img.shields.io/badge/Milvus-2.5-00a4e4)](https://milvus.io/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-purple)](https://platform.deepseek.com/)
[![Hit Rate](https://img.shields.io/badge/Hit%20Rate-90.91%25-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## 📋 目录

- [项目简介](#-项目简介)
- [系统架构](#%EF%B8%8F-系统架构)
- [核心特性](#-核心特性)
- [技术栈](#%EF%B8%8F-技术栈)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [检索评测](#-检索评测)
- [对话示例](#-对话示例)
- [License](#-license)

---

## 🎯 项目简介

FitChef 是一个**面向健身人群的垂直 RAG 问答系统**。系统先分类用户意图(纯知识 / 查个人数据 / 交叉分析),再选择最优处理路径——混合检索 1828 篇饮食知识 + 实时查询三模块个人数据(训练/体测/饮食),最后由 DeepSeek 生成个性化回答并 SSE 流式输出。

**这个项目能展示什么?**

- ✅ **完整 RAG 链路**:BM25 + bge-m3 向量并行 → RRF 融合 → Cross-Encoder 重排序 → 动态截断
- ✅ **意图路由**:三路决策(rag_only / data_query / rag_with_data),LLM 主判 + 信号词回退双保险
- ✅ **分层对话记忆**:长期摘要(LLM 压缩 2-3 句)+ 短期窗口(最近 4 轮原文),平衡 token 与上下文
- ✅ **个人数据交叉分析**:训练容量、体重趋势、营养摄入与知识库结果联合分析
- ✅ **全链路可观测**:LangFuse 追踪每阶段耗时/token/输入输出
- ✅ **评测可量化**:55 题内置评测集,Hit Rate **90.91%** / MRR **0.8415**

---

## 🏗️ 系统架构

### RAG 检索链路(6 步)

```
                                            POST /chat/rag (SSE)
                                                       │
                                                       ▼
   ┌────────────── ① Query Rewrite + 意图识别 ──────────────┐
   │  LLM 把口语→ keywords + semantic + intent             │
   │    ├─ data_query?     ──→ 查个人数据 → LLM 回复       │
   │    ├─ rag_with_data?  ──→ 知识检索 ∥ 个人数据 → 交叉分析│
   │    └─ rag_only?       ──→ 继续走下面 5 步             │
   └────────────────────────┬─────────────────────────────┘
                            ▼
   ┌─────────── ② 混合检索(并发) ──────────┐
   │   ┌──────────────┐  ┌──────────────┐  │
   │   │ BM25 关键词  │  │ 向量语义检索  │  │
   │   │ jieba 分词   │  │ bge-m3 1024d │  │
   │   │ rank_bm25    │  │ Milvus IVF   │  │
   │   │   Top-15     │  │   Top-15     │  │
   │   └──────┬───────┘  └──────┬───────┘  │
   └──────────┼─────────────────┼─────────┘
              └──────────┬──────┘
                         ▼
   ③ RRF 融合(k=10, 向量 0.85 / BM25 0.15) → Top-12
                         │
                         ▼
   ④ Cross-Encoder 重排序(bge-reranker-v2-m3) → Top-8
                         │
                         ▼
   ⑤ 短语加权 + 动态截断(标题匹配翻倍 + 分数落差) → Top-5
                         │
                         ▼
   ⑥ DeepSeek 流式生成 → SSE 逐 token 推送
```

> **异常降级**:向量失败 → 纯 BM25,重排失败 → 跳过重排。任何单点故障都不会让对话挂掉。

---

## ✨ 核心特性

### 1. 三路意图路由

**为什么需要意图路由?** 健身用户的问题混合度极高——"我体重在降但怕蛋白质不够怎么办"既要查个人数据,又要查营养知识。如果只走 RAG 会丢个人数据,只查数据库又给不出建议。

| 意图 | 触发 | 处理路径 | 示例 |
|------|------|----------|------|
| `rag_only` | 纯知识问题 | RAG 检索 → LLM 生成 | "减脂该吃多少蛋白质" |
| `data_query` | 查个人记录 | 查三模块数据 → LLM 格式化 | "我最近体重有什么变化" |
| `rag_with_data` | 个人数据 + 寻求建议 | 知识检索 ∥ 个人数据 → 交叉分析 | "我体重在降但训练没力气怎么办" |

**双保险**:LLM 首次分类 → 本地信号词回退(避免个人数据查询被误判为纯知识问题)。

### 2. 混合检索 + 重排序

| 策略 | Hit Rate | MRR | 命中数 |
|------|----------|-----|--------|
| BM25 关键词 | 70.91% | 0.6606 | 39/55 |
| 向量检索(bge-m3) | 90.91% | 0.8309 | 50/55 |
| **混合检索(RRF)** | **90.91%** | **0.8415** | **50/55** |

向量检索单跑 hit rate 已经追平混合检索,但 **MRR 不如混合**——混合检索把正确答案排得更靠前,直接影响 LLM context 质量。

### 3. 分层对话记忆

**问题**:聊到第 8 轮时全量传 messages 会爆 token,但只传最近几条会丢上下文(用户说"那个呢"模型不知道指什么)。

**解法**:两层分级。

| 层级 | 存储 | 容量 | 内容 | 更新方式 |
|------|------|------|------|----------|
| **短期窗口** | `messages` 表 | 最近 4 条 | 原始对话全文 | 自动滚动,旧消息脱落 |
| **长期摘要** | `conversations.summary` | 2-3 句 | LLM 压缩的关键信息 | 每轮异步累积更新 |

```
旧摘要 + 本轮对话 → LLM → 更新后摘要
```

摘要保留:健身目标、饮食偏好、已讨论的食材/菜谱。两个入口都会用到:
- **查询改写阶段** — 拼摘要 + 最近对话,让"再详细点"这类指代词能被解析
- **LLM 生成阶段** — 摘要注入 System Prompt,跨轮次记得用户目标

### 4. 个人数据三模块

| 模块 | 粒度 | 自动计算 |
|------|------|----------|
| **训练记录** | 动作级 + 组级 | 训练容量 = ∑(重量 × 次数),容量趋势 ↑↓ |
| **身体指标** | 体重 + 体脂率 | 周变化、SVG 折线趋势图 |
| **饮食日志** | 条目级 | 营养素换算(对接 1657 条食物成分库) |

Dashboard:体重趋势图 + 周均营养摄入 + 周训练统计,三卡片一览。

### 5. 全链路可观测(LangFuse)

每次 `/chat/rag` 自动生成一个 Trace,包含:`query_rewrite` → `hybrid_search` → `rerank` → `generate` 四个 Span,记录每阶段耗时、token 数、输入输出。线上排查"为什么这次回答不好"直接看 trace,不用 grep 日志。

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 (Composition API) + Vite 8 + vue-router 4 |
| **后端** | FastAPI + SQLAlchemy 2.0 async + aiomysql |
| **LLM** | DeepSeek API (OpenAI 兼容) + instructor (结构化 JSON 提取) |
| **向量库** | Milvus 2.5 + Ollama `bge-m3` (1024 维) |
| **关键词** | rank-bm25 + jieba 中文分词 |
| **重排序** | SentenceTransformers + `bge-reranker-v2-m3` (可选) |
| **关系库** | MySQL 8.0 |
| **可观测** | LangFuse (Trace/Span 全链路追踪) |
| **鉴权** | JWT (python-jose) + bcrypt |
| **日志** | Loguru |
| **容器** | Docker Compose (6 容器) |

---

## 🚀 快速开始

### 前置条件

- Python 3.11+,Node.js 22+,Docker Desktop
- DeepSeek API Key([申请](https://platform.deepseek.com/))
- Ollama + `bge-m3` 模型 (`ollama pull bge-m3`)

### 启动步骤

```bash
# 1. 起基础服务(MySQL :3307 / Milvus :19530 / LangFuse :3000)
docker compose up -d

# 2. Python 环境
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 配置环境变量(至少填 DEEPSEEK_API_KEY)
cp .env.example .env

# 4. 起后端
python run.py                # http://localhost:8000

# 5. 起前端(新终端)
cd frontend
npm install && npm run dev   # http://localhost:5173
```

打开 `http://localhost:5173` 注册账号即可。API 文档见 `http://localhost:8000/docs`。

> **首次启动**会自动建表 + 加载 1828 篇知识库 + 生成向量索引,可能需要几分钟。
> **MySQL 端口注意**:Docker 把 MySQL 映射到 host **3307**,本地跑后端时 `.env` 里 `DB_HOST=localhost`、`DB_PORT=3307`。

---

## 📁 项目结构

```
my_project1/
├── 📂 frontend/                    Vue 3 前端
│   └── src/
│       ├── views/                  Dashboard · WorkoutLog · BodyMetric · DietLog
│       ├── components/             ChatLayout · WeightChart · FoodSearch · WorkoutForm
│       └── services/api.js         API 调用 + SSE 流式处理
│
├── 📂 app/                         FastAPI 后端
│   ├── routers/                    auth · chat · workout · body_metric · diet · food
│   │
│   ├── services/                   ← 核心业务
│   │   ├── rag_chat_service.py        RAG 全链路编排(意图路由)
│   │   ├── query_rewriter_service.py  查询改写 + 意图识别
│   │   ├── personal_context.py        个人数据摘要(交叉分析用)
│   │   ├── hybrid_search_service.py   混合检索(BM25 + 向量 → RRF)
│   │   ├── reranker_service.py        Cross-Encoder 重排序
│   │   ├── conversation_service.py    会话管理 + 摘要生成
│   │   ├── workout_service.py         训练 CRUD + 容量统计
│   │   ├── body_metric_service.py     体测 CRUD + 趋势
│   │   ├── diet_service.py            饮食 CRUD + 营养统计
│   │   ├── food_db_service.py         食物成分库(1657 条)
│   │   ├── observability.py           LangFuse 追踪
│   │   └── eval_service.py            检索质量评测
│   │
│   ├── models/                     SQLAlchemy ORM
│   ├── schemas/                    Pydantic 校验
│   ├── core/                       config · database · security · logger
│   ├── data/                       知识库原始数据(食物表 / 食谱 / 膳食指南)
│   └── indexes/                    向量索引持久化
│
├── docker-compose.yml              6 容器编排
├── main.py · run.py                FastAPI 入口
└── requirements.txt
```

---

## 📊 检索评测

内置 55 道测试题,覆盖食材查询、食谱做法、营养知识三类场景。

```bash
curl -X POST http://localhost:8000/chat/eval \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"summary_only": true}'
```

| 策略 | Hit Rate | MRR |
|------|----------|-----|
| BM25 关键词 | 70.91% | 0.6606 |
| 向量(bge-m3) | 90.91% | 0.8309 |
| **混合(RRF)** | **90.91%** | **0.8415** |

---

## 💬 对话示例

**纯知识(rag_only)**

```
鸡胸肉每 100g 多少蛋白质?减脂期适合吃吗?
西兰花有什么营养价值?
番茄炒蛋怎么做?
```

**查个人数据(data_query)**

```
我最近体重有什么变化?
我这周练了几次?
看看我的饮食记录
```

**交叉分析(rag_with_data)**

```
我最近体重掉了但训练没力气怎么办?
我蛋白质摄入够不够影响增肌?
最近体重不掉了怎么办?
```

> `rag_with_data` 路径会**同时**查知识库和个人数据,融合两者生成个性化建议。

---

## 📄 License

[MIT License](./LICENSE) — 自由使用、修改、分发,保留版权声明即可。
