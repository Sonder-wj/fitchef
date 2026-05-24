# services/query_rewriter_service.py
# 职责：用 LLM 提取关键词，用于知识库检索

import instructor
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="query_rewriter")


class QueryRewriteResult(BaseModel):
    """查询改写结果"""
    keywords: str = Field(
        default="",
        description="用于 BM25 关键词检索，空格分隔的饮食/健身术语。与饮食无关时留空"
    )
    semantic: str = Field(
        description="用于向量语义检索，一句自然的查询表述"
    )
    intent: str = Field(
        default="rag_only",
        description="rag_only | data_query | rag_with_data"
    )


REWRITE_PROMPT = """你是健身饮食检索助手。用户问题可能偏口语化，你需要同时输出两种查询形式，用于两路不同检索。

规则：
- keywords: 提取核心饮食术语，像食材名、菜名、烹饪方式、营养素（蛋白质/碳水/脂肪/热量）、健身目标（减脂/增肌）。保留原词
- semantic: 把口语转成规范查询表述，保持自然语句形式，不要太长
- intent: 判断用户意图类型
  * "rag_only": 纯知识问题，不涉及用户个人数据。例："减脂该吃多少蛋白质""鸡胸肉怎么做"
  * "data_query": 用户查询自己的记录数据。例："我这周练了几次""我体重多少""看看我的饮食记录"
  * "rag_with_data": 用户问自己的情况并寻求分析建议。例："我最近体重不掉怎么办""我蛋白质吃不够影响大吗"
- 【重要】如果用户输入与饮食、健身、营养、食材、烹饪完全无关，keywords 必须严格输出空字符串 ""，semantic 保持原样。不要强行联想

判断无关话题的示例（keywords 必须为空）：
- 购物类："想买一件衣服"、"推荐手机" → keywords 留空
- 天气类："今天天气怎么样" → keywords 留空
- 闲聊类："讲个笑话"、"今天心情不好"、"推荐一部电影" → keywords 留空
- 注意：简单问候（"你好""嗨""在吗"）不算无关话题，将它们当作饮食咨询的开始，正常提取饮食关键词
- 科技类："Python怎么写" → keywords 留空

intent 判断示例：
- "减脂晚上吃什么" → intent: "rag_only"
- "我最近一周练了几次" → intent: "data_query"
- "我最近体重有什么变化" → intent: "data_query"
- "看看我的饮食记录" → intent: "data_query"
- "我最近体重不掉了怎么办" → intent: "rag_with_data"
- "我这周蛋白质摄入够吗" → intent: "rag_with_data"

饮食健身相关的示例：
"减肥晚上吃什么" → keywords: "减脂 晚餐 低卡 高蛋白 蔬菜", semantic: "减脂期晚餐适合吃什么，有哪些低热量高蛋白的晚餐选择和食谱", intent: "rag_only"
"鸡胸肉怎么做好吃又不柴" → keywords: "鸡胸肉 烹饪 嫩 不柴 做法", semantic: "鸡胸肉怎么烹饪才能嫩而不柴，有哪些做法和技巧", intent: "rag_only"
"增肌一天要吃多少蛋白质" → keywords: "增肌 蛋白质 摄入量 每日", semantic: "增肌期每天需要摄入多少蛋白质，如何计算和分配", intent: "rag_only"
"这玩意热量高不高" → keywords: "热量 高 食物", semantic: "常见高热量食物有哪些，每100g热量多少大卡", intent: "rag_only"
"太胖了咋办" → keywords: "减脂 饮食 控制 热量", semantic: "减脂期应该如何调整饮食，有哪些低热量食物和饮食方案", intent: "rag_only"
"想买一件衣服" → keywords: "", semantic: "想买一件衣服", intent: "rag_only"
"我最近一周体重掉了1.5kg但是训练没力气怎么办" → keywords: "减脂 蛋白质 训练恢复 热量", semantic: "减脂期体重下降快但训练无力，如何调整饮食和训练", intent: "rag_with_data"

用户问题：{query}"""


# 本地意图信号词（不依赖 LLM，确保个人数据查询不被漏掉）
_DATA_QUERY_SIGNALS = [
    "我练了", "我训练", "我的训练", "练了几次", "训练了几次",
    "我体重", "我的体重", "体重多少", "体重变化", "体重趋势",
    "我吃了", "我的饮食", "饮食记录", "今天吃了", "这周吃了",
    "我身体", "体脂", "体脂率",
]
_RAG_WITH_DATA_SIGNALS = [
    "我最近体重不掉", "体重不掉", "平台期", "不掉秤",
    "我蛋白质吃不够", "我蛋白质不够", "我吃不够",
    "影响大吗", "怎么办", "帮我分析", "给我建议",
    "我训练没力气", "训练没状态", "恢复不过来",
]


def _local_intent(query: str) -> str:
    """本地意图回退检测：如果 LLM 未能正确识别，通过信号词补充"""
    for s in _DATA_QUERY_SIGNALS:
        if s in query:
            for s2 in _RAG_WITH_DATA_SIGNALS:
                if s2 in query:
                    return "rag_with_data"
            return "data_query"
    return "rag_only"


class QueryRewriterService:
    def __init__(self):
        base_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
        self.model = settings.DEEPSEEK_MODEL

    async def rewrite(self, query: str) -> dict:
        try:
            result = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": REWRITE_PROMPT.format(query=query)}],
                response_model=QueryRewriteResult,
                temperature=0.3,
                max_tokens=200,
            )
            keywords = result.keywords.strip()
            semantic = result.semantic.strip() or query
            intent = getattr(result, "intent", "rag_only") or "rag_only"

            # 本地信号词回退：LLM 可能把个人数据问题误判为 rag_only
            local = _local_intent(query)
            if intent == "rag_only" and local != "rag_only":
                logger.info(f"意图回退: LLM={intent} → local={local}")
                intent = local

            logger.info(f"查询优化: '{query}' → keywords='{keywords}' intent={intent}")
            return {
                "original": query,
                "keywords": keywords,
                "semantic": semantic,
                "intent": intent,
                "changed": keywords != "" or semantic != query,
            }
        except Exception as e:
            logger.warning(f"查询优化出错，回退原查询: {e}")
            local_intent = _local_intent(query)
            return {
                "original": query,
                "keywords": query,
                "semantic": query,
                "intent": local_intent,
                "changed": False,
            }


query_rewriter_service = QueryRewriterService()
