# services/conversation_service.py
# 职责：对话和消息的增删改查业务逻辑

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from app.models.conversation import Conversation, DialogueType
from app.models.message import Message
from openai import AsyncOpenAI
from app.core.config import settings
from fastapi import HTTPException

# 复用 AsyncOpenAI client，避免每次调用都重新建连
_llm_client = None

def _get_llm_client():
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
    return _llm_client


# 摘要是积累式的，所以用 markdown 分隔
SUMMARY_PROMPT = """你是对话摘要助手。根据旧摘要和新对话，生成一个更新的摘要（2-3句话）。

规则：
- 提炼关键信息：用户的健身目标（减脂/增肌）、饮食偏好、已讨论的食材/菜谱/营养素、用户反馈
- 如果旧摘要已有内容，把新信息融入进去，不要重复
- 只输出摘要本身，不要前缀

示例：
旧摘要：用户想减脂，已询问鸡胸肉的做法
新对话：
用户: 鸡胸肉热量多少
AI: 每100g鸡胸肉含24g蛋白质、1.2g脂肪、133大卡热量，减脂期推荐

更新后：用户想减脂，已讨论鸡胸肉的做法和热量（每100g含24g蛋白质、133大卡）

旧摘要：无
新对话：
用户: 晚上吃什么不长胖
AI: 建议选择高蛋白低脂的食物，如清蒸鱼、鸡胸肉、豆腐配蔬菜，避免高碳水主食

更新后：用户关注减脂晚餐，已推荐清蒸鱼、鸡胸肉、豆腐等高蛋白低脂选择

旧摘要：{old_summary}
新对话：
{new_messages}

更新后的摘要："""


class ConversationService:

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: int,
        dialogue_type: DialogueType = DialogueType.NORMAL
    ) -> Conversation:
        """
        创建新对话
        如果用户已有一个空的"新会话"（还没发过消息），直接复用，不重复创建
        """
        # 查找该用户是否有未使用的新会话（标题是"新会话"且没有消息）
        result = await db.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.title == "新会话",
                Conversation.dialogue_type == dialogue_type
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # 复用已有的空会话

        # 创建新会话
        conversation = Conversation(
            user_id=user_id,
            title="新会话",
            dialogue_type=dialogue_type
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod #静态方法: 没有self,不依赖实例
    async def save_message(
        db: AsyncSession,
        conversation_id: int,
        user_content: str,      # 用户发的消息
        assistant_content: str  # AI 回复的消息
    ) -> None:
        """
        保存一轮对话（用户消息 + AI回复）到数据库
        同时在第一条消息时自动生成会话标题
        """
        # 查询会话是否存在
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 如果还是"新会话"标题，说明是第一条消息，自动生成标题
        if conversation.title == "新会话":
            title = await ConversationService._generate_title(user_content)
            conversation.title = title

        # 更新会话的最后修改时间
        conversation.updated_at = datetime.now()

        # 保存用户消息
        user_msg = Message(
            conversation_id=conversation_id,
            sender="user",
            content=user_content
        )
        # 保存 AI 回复
        assistant_msg = Message(
            conversation_id=conversation_id,
            sender="assistant",
            content=assistant_content
        )

        db.add(user_msg)
        db.add(assistant_msg)
        await db.commit()

    @staticmethod
    async def _generate_title(user_content: str) -> str:
        """
        根据用户第一条消息，调用 LLM 自动生成会话标题
        标题控制在10个字以内
        """
        try:
            client = _get_llm_client()
            resp = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[{"role": "system", "content": """根据用户的第一条消息生成会话标题。

规则：
- 不超过10个字
- 提炼核心主题，不要照搬原话
- 只输出标题本身，不要加引号、句号、任何前缀

示例：
"鸡胸肉怎么做好吃又不柴" → 鸡胸肉做法
"减脂期晚上可以吃什么" → 减脂晚餐
"增肌一天需要摄入多少蛋白质" → 增肌蛋白质摄入
"番茄炒蛋的热量是多少" → 番茄炒蛋热量
"便秘吃什么能改善" → 改善便秘饮食
"想减肥" → 减肥饮食"""},
                {"role": "user", "content": user_content}
            ])
            title = resp.choices[0].message.content
            return title.strip()[:20]
        except Exception:
            # 生成失败就用消息前10个字作为标题
            return user_content[:10] + ("..." if len(user_content) > 10 else "")

    @staticmethod
    async def get_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
        """获取用户的所有对话，按最后更新时间倒序"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.status == "ongoing")
            .order_by(desc(Conversation.updated_at))
        )
        return result.scalars().all()

    @staticmethod
    async def get_messages(db: AsyncSession, conversation_id: int, limit: int = 20) -> list[Message]:
        """获取对话最近的消息，按时间正序"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        messages.reverse()  # 恢复正序
        return messages

    @staticmethod
    async def update_summary(conversation_id: int, new_messages: str) -> str:
        """用 LLM 更新对话摘要（独立 session，可后台运行）"""
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                return ""

            old_summary = conv.summary or "无"
            try:
                client = _get_llm_client()
                resp = await client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "user", "content": SUMMARY_PROMPT.format(
                        old_summary=old_summary,
                        new_messages=new_messages
                    )}],
                    temperature=0.3,
                    max_tokens=150,
                )
                conv.summary = resp.choices[0].message.content.strip()[:300]
                await db.commit()
                return conv.summary
            except Exception:
                return old_summary

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: int, user_id: int) -> None:
        """删除对话（同时级联删除所有消息）"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id  # 确保只能删自己的对话
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        await db.delete(conversation)
        await db.commit()