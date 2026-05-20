# FitChef 个人数据追踪 + RAG 交叉分析 设计文档

## 问题

FitChef 目前是一个纯 RAG 问答助手——用户提问，系统检索知识库，LLM 生成回答。但健身饮食领域的通用知识，大模型训练数据中已充分覆盖。面试中被问"你的项目跟直接问 ChatGPT 有什么区别？"时缺乏说服力。

## 核心洞察

大模型能告诉你"减脂每天该吃多少蛋白质"，但不知道你今天实际吃了多少、上周练了什么、体重怎么变的。

**给 RAG 增加第二个上下文维度：用户个人数据。**

```
普通 RAG：   用户问题 → [知识库文档] → LLM → 通用建议
本方案：     用户问题 → [知识库文档 + 用户个人数据] → LLM → 个性化建议
```

## 功能范围

在现有 RAG 问答基础上，增加三个追踪模块：

| 模块 | 粒度 | 记录内容 |
|------|------|----------|
| 训练记录 | 动作级 | 训练会话 → 多个动作 → 每组重量×次数 |
| 身体指标 | 基础 | 日期 + 体重 + 体脂率 |
| 饮食日志 | 食物条目级 | 每餐拆食物条目 → 重量 → 自动算营养素 |

三个模块均可独立使用（CRUD），核心差异化在 RAG 交叉分析层。

## 数据模型

### 训练记录（三层）

```
workout (训练会话)    1 ── N workout_exercise (训练动作)    1 ── N workout_set (训练组)
```

**workout**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| user_id | int | FK |
| date | date | 训练日期 |
| body_part | varchar(20) | 胸/背/腿/肩/臂/全身 |
| duration_min | int | 可选 |
| notes | text | 可选 |

**workout_exercise**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| workout_id | int | FK |
| exercise_name | varchar(100) | 杠铃卧推/深蹲等 |
| sort_order | int | 动作顺序 |

**workout_set**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| exercise_id | int | FK |
| set_number | int | 第几组 |
| weight_kg | float | 重量 |
| reps | int | 次数 |

训练容量 = SUM(weight_kg × reps)，可通过 SQL 直接聚合计算趋势。

### 身体指标

**body_metric**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| user_id | int | FK |
| date | date | 测量日期 |
| weight_kg | float | 体重 |
| body_fat_pct | float | 体脂率，可空 |
| notes | text | 可选 |

体脂率可空——没体脂秤的用户也能用。前端引导：体重可每天记，体脂每周一次足矣。

### 饮食日志（两层）

```
diet_meal (饮食记录)    1 ── N diet_food_item (食物条目)
```

**diet_meal**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| user_id | int | FK |
| date | date | 日期 |
| meal_type | enum | breakfast/lunch/dinner/snack |
| total_calories | float | 汇总（冗余存储，方便查询） |
| total_protein | float | 同上 |
| total_fat | float | 同上 |
| total_carbs | float | 同上 |

**diet_food_item**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| meal_id | int | FK |
| food_name | varchar(100) | 匹配食物库 |
| amount_g | float | 吃了多少克 |
| calories | float | 存储时计算：食物库每100g值 × (amount_g/100) |
| protein_g | float | 同上 |
| fat_g | float | 同上 |
| carbs_g | float | 同上 |

营养素值在用户录入时从食物库计算并冗余存储，原因：食物库后续更新不影响历史记录；趋势查询无需每次 join 计算；食物库中条目被移除时历史仍完整。

### 食物营养数据库

复用现有 `app/data/china_food_composition.json`（1657 种中国食物成分表数据），每条含每100g 的热量、蛋白质、脂肪、碳水、微量元素。

复合菜品（如鱼香肉丝）无法精确匹配时，用户可搜索近似主要食材替代。

### 用户目标（可选）

为交叉分析提供基准线：

**user_goal**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PK |
| user_id | int | FK（unique） |
| goal_type | enum | cut/bulk/maintain |
| daily_calories | int | 目标热量 |
| daily_protein_g | int | 目标蛋白质 |

## RAG 集成方案

### 三层路由

在现有 Query Rewrite 步骤中，LLM 同时输出 intent 字段，不做额外 API 调用：

```
System: 你是 FitChef 的查询分析器。分析用户输入，输出 JSON：
{
  "rewritten_query": "...",
  "keywords": "...",
  "intent": "rag_only" | "data_query" | "rag_with_data"
}

判断规则：
- rag_only：纯知识问题。例："减脂该吃多少蛋白质""生酮饮食的原理"
- data_query：用户查自己的数据。例："我这周练了几次""我体重多少"
- rag_with_data：问"我的情况+该怎么办"，需数据与知识交叉分析。
  例："我最近体重不掉怎么办""我蛋白质吃不够影响大吗"
```

- **rag_only** → 现有 RAG 管线，不改动
- **data_query** → 查 MySQL → LLM 格式化自然语言返回
- **rag_with_data** → 知识检索 + 个人数据查询（并行）→ 上下文融合 → LLM 生成

### rag_with_data 流程

```
用户问题
  │
  ▼
Query Rewrite + Intent（1 次 LLM 调用）
  │
  ├─ parallel ─────────────────┐
  │                            │
  ▼                            ▼
知识库检索                  个人数据查询
BM25 + 向量 + RRF           ├─ 时间范围提取（"最近一周" → 7天）
  │                         ├─ 模块判断（问题涉及 diet/body/workout 哪些）
  ▼                         ├─ diet: 日均营养素 + 热量缺口
知识库 Top-5 文档           ├─ body: 体重变化趋势
  │                         ├─ workout: 训练容量趋势 + 频率
  │                         └─ goal: 目标对比（缺口/超出）
  │                            │
  └────────┬───────────────────┘
           ▼
      上下文拼装
      ├─ 知识库文档（搜索结果原文）
      └─ 个人数据摘要（预处理后的结构化数据，非原始行）
           ▼
      LLM 流式生成
           ▼
      个性化建议 + 数据引用
```

### 关键设计：预处理摘要而非原始数据

LLM 不应看到数据库原始行，而是预计算后的摘要：

```python
personal_context = """
【用户近况 最近7天】
- 日均热量摄入：1680 kcal（目标：2000，缺口 16%）
- 日均蛋白质：45g（建议 ≥65g，实际缺口 31%）
- 体重变化：78.5kg → 77.0kg（↓1.5kg）
- 训练容量趋势：↓12%（3次训练，5200→4800→4500kg）

【关键信号】
- 蛋白质摄入连续 7 天不足建议值
- 体重下降速度偏快（健康：0.5-1kg/周）
- 训练容量同步下降，提示恢复不足或热量缺口过大
"""
```

### 异常检测（后续迭代）

后台定时任务扫描用户数据，触发异常信号：

| 异常 | 检测规则 | 生成建议 |
|------|----------|----------|
| 平台期 | 体重连续 14 天变化 < 0.3kg | 建议调整热量或训练策略 |
| 蛋白质持续偏低 | 连续 7 天低于目标 80% | 高蛋白食物推荐 |
| 训练容量持续下降 | 连续 2 周容量下降 > 10% | 提示恢复不足/减载 |

## 前端页面

### 新增页面

| 页面 | 路由 | 内容 |
|------|------|------|
| Dashboard | `/dashboard` | 体重趋势图 + 训练容量曲线 + 本周营养摘要 + 异常提醒卡片 |
| 训练记录 | `/workout` | 列表 + 新增/编辑表单（动作自动补全，预填上次重量） |
| 身体指标 | `/body` | 列表 + 体重折线图 + 新增表单 |
| 饮食日志 | `/diet` | 按日期+餐次分组列表 + 新增（搜索食物 → 选条目 → 填重量 → 自动算） |

### 现有页面改动

| 页面 | 改动 |
|------|------|
| 聊天页 `/chat` | 回答中支持引用个人数据的具体数字 |

## 后端 API

### 新增路由

```
POST   /api/workout          创建训练记录
GET    /api/workout           训练列表（支持日期范围）
GET    /api/workout/:id       训练详情
PUT    /api/workout/:id       编辑
DELETE /api/workout/:id       删除
GET    /api/workout/exercises 历史动作名列表（自动补全用）

POST   /api/body-metric      创建身体指标
GET    /api/body-metric        列表
PUT    /api/body-metric/:id    编辑
DELETE /api/body-metric/:id    删除

POST   /api/diet-meal         创建饮食记录（含食物条目）
GET    /api/diet-meal          列表（按日期范围+餐次）
PUT    /api/diet-meal/:id      编辑
DELETE /api/diet-meal/:id      删除

GET    /api/food/search?q=鸡胸  食物搜索（匹配 china_food_composition）
GET    /api/food/:id            食物详情（每100g营养素）

POST   /api/chat/rag           现有点，Query Rewrite 增加 intent 输出
```

### 改动现有文件

| 文件 | 改动 |
|------|------|
| `app/services/rag_chat_service.py` | Query Rewrite 增加 intent；新增 rag_with_data 分支 |
| `app/services/query_rewriter_service.py` | prompt 增加 intent 输出 |
| `app/routers/chat.py` | 路由逻辑适配三种 intent |
| `app/models/` | 新增 workout/body_metric/diet 模型 |

## 项目结构（新增部分）

```
app/
├── models/
│   ├── workout.py
│   ├── body_metric.py
│   └── diet.py
├── schemas/
│   ├── workout.py
│   ├── body_metric.py
│   └── diet.py
├── routers/
│   ├── workout.py
│   ├── body_metric.py
│   └── diet.py
├── services/
│   ├── workout_service.py
│   ├── body_metric_service.py
│   ├── diet_service.py
│   ├── food_db_service.py      # 食物库搜索
│   └── personal_context.py     # 个人数据摘要构建
frontend/src/
├── views/
│   ├── Dashboard.vue
│   ├── WorkoutLog.vue
│   ├── BodyMetric.vue
│   └── DietLog.vue
├── components/
│   ├── WeightChart.vue
│   ├── WorkoutForm.vue
│   ├── DietMealForm.vue
│   └── FoodSearch.vue
```

## 误差与局限

营养计算存在天然误差：
- **用户估重**：中餐份量难以精确（"一碗饭"到底多少），可通过常用份量换算降低门槛
- **复合菜品**：鱼香肉丝等无法精确匹配单一食材，用户选近似主要食材替代
- **体脂率**：家用体脂秤误差 ±3-5%，趋势比绝对值更有意义

面试时坦诚这些局限是加分项——说明你理解系统的工程边界。

## 面试叙事

> "我做的 FitChef 最初是 RAG 问答。但后来我发现一个问题：用户问'怎么减脂'，我的系统能回答，ChatGPT 也能回答。于是我加了一层——用户记录自己的训练、身体、饮食数据，系统在回答时会把个人数据跟知识库文档交叉分析。
>
> 比如用户问'我体重不掉怎么办'，系统会先在知识库检索平台期相关文章，同时查他近两周的饮食热量、蛋白质摄入、训练容量变化，计算摘要后与知识库文档一起交给 LLM 做交叉分析，生成引用他具体数据的个性化建议。
>
> 这就是大模型做不到的事——它不知道你昨天吃了什么、上周练了什么。"

## 技能链路

| 阶段 | 技能 | 状态 |
|------|------|------|
| 设计 | `/brainstorming` | 当前 |
| 规划 | `writing-plans` | 下一步 |
| 实现 | `subagent-driven-development` | 等待规划完成 |
| 验证 | `verification-before-completion` | 等实现时逐模块 |
| 调试 | `systematic-debugging` | 遇到问题时 |
