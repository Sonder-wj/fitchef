# services/rag_chat_service.py
# 职责：RAG 对话完整流程
# 查询改写 → 混合检索 → 重排序 → 构建上下文 → 流式生成
# FitChef — 健身餐营养助手

from typing import AsyncGenerator, Optional, Callable, List, Dict
import json
import asyncio
import time
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import get_logger
from app.services.fitchef_loader import fitchef_loader, FitChefDocument
from app.services.hybrid_search_service import hybrid_search_service
from app.services.reranker_service import reranker_service
from app.services.query_rewriter_service import query_rewriter_service
from app.services.observability import RagTrace

logger = get_logger(service="rag_chat")


def _safe_background(coro, name: str = ""):
    """创建后台任务，异常自动记录日志（避免 fire-and-forget 吞异常）"""
    task = asyncio.create_task(coro)
    def _on_done(t):
        exc = t.exception()
        if exc:
            logger.error(f"后台任务 [{name}] 异常: {exc}")
    task.add_done_callback(_on_done)
    return task

FITCHEF_SYSTEM_PROMPT = """你是一位专业的健身饮食顾问 FitChef，基于知识库为用户提供准确的营养和饮食建议。

## 回答格式规范
- 第一段用一两句话直接给出核心结论
- 后续段落展开说明，关键数据（热量、蛋白质、碳水数值）用 **加粗** 突出
- 涉及步骤或多个要点时，用数字序号分行列出
- 段落之间空一行
- 引用来源编号用 [1] [2] 标注在相关句末
- 不确定的内容必须明确说"知识库中未收录该信息"，不要猜测

## 风格要求
- 禁止口语化表达（"说实话""对了""说白了""哈哈"等）
- 禁止反问用户（"你平时吃什么？"等）
- 专业、准确、简洁

## 回答示例

用户问："鸡胸肉每100g多少蛋白质？减脂期适合吃吗？"

✅ 正确回答：
鸡胸肉每100g约含 **24g蛋白质**、**1.2g脂肪**、**133大卡热量**，是减脂期最推荐的蛋白质来源之一 [1]。

减脂期吃鸡胸肉的优势：
1. 蛋白质含量高、脂肪极低，有助于维持肌肉同时控制热量
2. 饱腹感强，200g鸡胸肉仅约260大卡，搭配蔬菜就是一顿合格的减脂餐
3. 建议用水煮、煎（少油）或凉拌方式烹饪，避免油炸增加不必要的热量 [1]

❌ 错误回答（禁止出现）：
鸡胸肉含有蛋白质，热量也比较低。说实话减脂期吃很不错，你可以平时多吃点，要不要我给你推荐个食谱？

## 当前参考内容
以下每条前面有编号 [N]，请在回答中引用：
{context}"""

OFF_TOPIC_PROMPT = "用户的问题与健身饮食无关。请说明你是饮食营养助手，无法回答该问题，并请用户提出饮食相关的问题。语气保持专业。"

LOW_SCORE_PROMPT = """你是一位专业的健身饮食顾问 FitChef。

重要：知识库中**未检索到与用户问题高度匹配的内容**。你必须严格遵守以下规则：

1. 开头第一句必须明确告知用户："知识库中未收录该问题的相关信息"
2. 如果你具备相关营养学常识，可以给出一般性参考建议，但必须在建议前加一句"以下是基于营养学常识的建议，仅供参考"
3. 禁止编造任何具体数值（热量、克数、百分比等）。不记得准确数据就说"建议查阅营养标签或咨询专业营养师"
4. 不要引用任何来源编号
5. 保持专业、简洁

## 回答示例

用户问："隔夜燕麦和新鲜燕麦营养有什么区别？"

✅ 正确回答：
知识库中未收录该问题的相关信息。

以下是基于营养学常识的建议，仅供参考：隔夜燕麦和新鲜燕麦在主要营养成分（碳水、蛋白质、膳食纤维）上差异不大。隔夜浸泡主要改变了淀粉的结构，部分抗性淀粉增加，可能略微降低血糖反应。具体的营养变化数值建议查阅营养标签或咨询专业营养师。

❌ 错误回答（禁止）：
隔夜燕麦的碳水含量会降低约15%，蛋白质提高10%... [1][2]"""


def _extract_query_phrases(query: str) -> list:
    """从查询中提取可能的菜名/食材短语，用于精确标题匹配"""
    phrases = []
    cleaned = query.strip()
    for suffix in ["怎么做", "怎么做好吃", "怎么吃", "是什么", "的营养", "每100g", "的热量", "好不好"]:
        cleaned = cleaned.replace(suffix, "")
    if cleaned.strip() and len(cleaned.strip()) >= 2:
        phrases.append(cleaned.strip())
    if query.strip() not in phrases:
        phrases.append(query.strip())
    return phrases


class RAGChatService:
    """RAG 对话服务"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL
        self.is_ready = False

    async def generate_stream(
        self,
        query: str,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        on_complete: Optional[Callable] = None,
        history: list = None,
        summary: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        RAG 流式对话主流程
        history: 最近几轮原始消息
        summary: LLM 压缩的历史摘要（长期记忆）
        """
        if not self.is_ready:
            yield f"data: {json.dumps({'type': 'error', 'msg': 'RAG服务未初始化，请等待片刻后重试'}, ensure_ascii=False)}\n\n"
            return

        try:
            if history is None:
                history = []
            t_start = time.time()
            trace = RagTrace(query)

            # ── 用摘要 + 最近 2 轮做查询改写 ──
            context_query = query
            if summary or history:
                parts = []
                if summary:
                    parts.append(f"对话背景: {summary}")
                recent = history[-4:]
                if recent:
                    parts.append("最近对话: " + " ".join([h['content'][:50] for h in recent]))
                if parts:
                    context_query = " | ".join(parts) + f" | 当前问题: {query}"

            # ── Step 1: 查询改写（双路：关键词+语义）──
            rewrite_span = trace.span("query-rewrite", input={"context_query": context_query[:200]})
            rewrite_result = await query_rewriter_service.rewrite(context_query)
            keywords = rewrite_result.get("keywords", query)
            semantic = rewrite_result.get("semantic", query)
            t_rewrite = time.time()
            rewrite_span.end(output={"keywords": keywords, "semantic": semantic})
            yield f"data: {json.dumps({'type': 'query_rewrite', 'original': query, 'keywords': keywords, 'semantic': semantic}, ensure_ascii=False)}\n\n"

            # ── 话题拦截：查询改写出不了饮食关键词 → 交给 LLM 处理，不拦截 ──
            keywords_str = (keywords or "").strip()
            low_confidence = (not keywords_str or keywords_str == query.strip())

            if low_confidence:
                # 可能无关话题，但让 LLM 自己判断——不预判拦截
                logger.info(f"低置信度查询（交由 LLM 自行判断）: {query[:80]}")

            # ── Step 2: 混合检索（BM25 用关键词，向量用语义）──
            search_span = trace.span("hybrid-search", input={"bm25_query": keywords, "vector_query": semantic})
            search_result = await hybrid_search_service.search(
                query=query, bm25_query=keywords, vector_query=semantic, top_k=12
            )
            results = search_result.get("results", [])
            t_search = time.time()
            search_span.end(output={"candidates": len(results)})
            logger.info(f"Step 1/5 混合检索完成: {len(results)} 条候选, 耗时 {t_search - t_rewrite:.2f}s")

            # ── Step 3: 重排序 ──
            if settings.RAG_USE_RERANK:
                logger.info("Step 2/5 重排序开始...")
                rerank_span = trace.span("rerank", input={"top_k": 8})
                rerank_result = await reranker_service.rerank(semantic, results, top_k=8)
                final_results = rerank_result.get("results", results)
                t_rerank = time.time()
                best = final_results[0].get("rerank_score", 0) if final_results else 0
                rerank_span.end(output={"final_count": len(final_results), "best_score": best})
                logger.info(f"Step 2/5 重排序完成: {len(final_results)} 条, best_score={best:.4f}, 耗时 {t_rerank - t_search:.2f}s")
            else:
                logger.info("Step 2/5 重排序已跳过 (RAG_USE_RERANK=False)")
                final_results = results
                t_rerank = t_search
                rerank_result = {"reranked": False}

        # ── Step 4: 精确短语匹配加权 ──
            # 用户查询中的关键词短语如果出现在文档标题中，该文档分数加倍
            query_phrases = _extract_query_phrases(query)
            logger.info(f"Step 3/5 短语匹配加权: phrases={query_phrases}")
            boost_count = 0
            for r in final_results:
                content = r.get("content", "")
                title = ""
                if content.startswith("【") and "】" in content[:30]:
                    after_bracket = content[content.index("】")+1:]
                    title = after_bracket.split("\n")[0].strip()
                for phrase in query_phrases:
                    if phrase and len(phrase) >= 2 and phrase in title:
                        old_score = r.get("rerank_score", r.get("rrf_score", r.get("score", 0)))
                        for key in ("rerank_score", "rrf_score", "score"):
                            if key in r:
                                r[key] = r[key] * 2.0
                                break
                        logger.info(f"Phrase boost: '{phrase}' matched title '{title}', score {old_score:.4f} -> {r.get(key, 0):.4f}")
                        boost_count += 1
                        break
            # 按分重新排序
            final_results.sort(
                key=lambda x: x.get("rerank_score", x.get("rrf_score", x.get("score", 0))),
                reverse=True
            )

            # ── Step 5: 动态截断（分数落差检测）──
            # 从第二个结果开始，如果分数骤降到前一个的 85% 以下，说明后面都是噪音
            for i in range(1, len(final_results)):
                prev = final_results[i-1].get("rerank_score", final_results[i-1].get("rrf_score", 0))
                curr = final_results[i].get("rerank_score", final_results[i].get("rrf_score", 0))
                if prev > 0 and curr / prev < 0.85:
                    final_results = final_results[:i]
                    break
            # 上限 5 篇
            final_results = final_results[:5]

            logger.info(f"Step 3/5 完成: {len(final_results)} 篇送入 LLM, boost={boost_count}")

            # ── 二次拦截：仅当检索完全失败才回退（让 LLM 自行处理模糊情况）──
            if not final_results:
                refusal = "抱歉，知识库中未收录该问题的相关信息。我是健身饮食助手 FitChef，可以为您解答减脂、增肌、日常营养、食材选择、菜谱查询等饮食相关问题。请问您想了解哪方面的饮食知识？"
                yield f"data: {json.dumps({'type': 'off_topic', 'msg': refusal}, ensure_ascii=False)}\n\n"
                return

            # 发送重排序对比（如果进行了重排序）
            if rerank_result.get("reranked"):
                yield f"data: {json.dumps({'type': 'rerank', 'before': rerank_result.get('before', []), 'after': rerank_result.get('after', [])}, ensure_ascii=False)}\n\n"

            # 发送检索结果（重排后的最终结果）
            yield f"data: {json.dumps({'type': 'search_results', 'total': len(final_results), 'results': [{'content': r['content'][:300], 'score': r.get('rerank_score', r.get('rrf_score', r.get('score', 0))), 'doc_id': r['doc_id']} for r in final_results]}, ensure_ascii=False)}\n\n"

            # ── 构建带引用的上下文 ──
            sources = []
            context_parts = []
            for idx, r in enumerate(final_results):
                content = r["content"]
                # 提取来源名称（格式：【食材】鸡胸肉\n... 或 【食谱】番茄炒蛋\n...）
                name = "未知"
                if content.startswith("【") and "】" in content[:20]:
                    name = content[1:content.index("】")]
                sources.append({"ref": idx + 1, "name": name, "doc_id": r.get("doc_id", idx), "score": r.get("rrf_score", r.get("score", 0))})
                context_parts.append(f"[{idx + 1}] {content}")
            combined_context = "\n---\n".join(context_parts)

            # 发送引用来源信息
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

            # ── 构建对话消息 ──
            if not final_results or (final_results[0].get("rrf_score", final_results[0].get("score", 0)) < 0.003):
                system_prompt = LOW_SCORE_PROMPT
                if summary:
                    system_prompt += f"\n\n对话背景：{summary}"
                messages = [{"role": "system", "content": system_prompt}]
                for h in history[-6:]:
                    messages.append(h)
                messages.append({"role": "user", "content": query})
            else:
                system_prompt = FITCHEF_SYSTEM_PROMPT.format(context=combined_context)
                if summary:
                    system_prompt += f"\n\n对话背景：{summary}"
                messages = [{"role": "system", "content": system_prompt}]
                for h in history[-4:]:
                    messages.append(h)
                messages.append({"role": "user", "content": query})

            try:
                logger.info(f"Step 4/5 LLM 生成开始, model={self.model}, context_docs={len(context_parts)}")
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.5,
                )

                llm_span = trace.span("llm-generation", input={"model": self.model, "msg_count": len(messages)})
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps(content, ensure_ascii=False)}\n\n"

                t_llm = time.time()
                llm_span.end(output={"response_length": len(full_response)})

                # 耗时汇总
                logger.info(
                    f"Step 5/5 RAG pipeline 完成 [{query[:30]}]: "
                    f"rewrite={t_rewrite - t_start:.2f}s "
                    f"search={t_search - t_rewrite:.2f}s "
                    f"rerank={t_rerank - t_search:.2f}s "
                    f"llm={t_llm - t_rerank:.2f}s "
                    f"total={t_llm - t_start:.2f}s "
                    f"tokens≈{len(full_response)}chars"
                )

                if on_complete:
                    await on_complete(full_response)

            except Exception as e:
                logger.error(f"LLM 生成出错: {e}")
                yield f"data: {json.dumps('生成回答时出错，请稍后重试。', ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"RAG 流程异常: {e}")
            yield f"data: {json.dumps('系统处理异常，请稍后重试。如果问题持续存在，请联系管理员。', ensure_ascii=False)}\n\n"


# 全局单例
rag_chat_service = RAGChatService()
