"""论文分析Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from utils.message_types import SummaryData, AnalysisData
from knowledge_base.chroma_manager import ChromaManager
from knowledge_base.embedding_service import EmbeddingService
from loguru import logger


@type_subscription(topic_type="AnalyzerAgent")
class AnalyzerAgent(RoutedAgent):
    """分析Agent - 结合知识库进行深度分析"""
    
    def __init__(
        self,
        model_client: ChatCompletionClient,
        chroma_manager: ChromaManager,
        embedding_service: EmbeddingService
    ):
        super().__init__("分析Agent")
        self._model_client = model_client
        self._chroma = chroma_manager
        self._embedding = embedding_service
        self._system_message = SystemMessage(
            content="""你是领域分析专家。基于论文摘要和相关文献，进行深度分析：
1. 技术创新点
2. 与现有研究的关系
3. 应用前景
4. 关键概念提取（3-5个关键术语）

输出格式：
分析内容：xxx
关键概念：概念1, 概念2, 概念3"""
        )
    
    @message_handler
    async def handle_summary(self, message: SummaryData, ctx: MessageContext) -> None:
        """处理摘要数据"""
        logger.info(f"分析论文: {message.title[:30]}...")
        
        # 检索相似论文
        query_text = f"{message.title} {message.summary.get('research_problem', '')}"
        query_embedding = self._embedding.encode_single(query_text)
        similar_papers = self._chroma.retrieve_similar(query_embedding, n_results=3)
        
        # 构建上下文
        context = "相关文献：\n"
        if similar_papers['documents'][0]:
            for i, doc in enumerate(similar_papers['documents'][0][:2]):
                context += f"{i+1}. {doc[:100]}...\n"
        else:
            context = "暂无相关文献"
        
        # 分析
        prompt = f"""论文：{message.title}
研究问题：{message.summary.get('research_problem', '')}
方法：{message.summary.get('method', '')}
价值：{message.summary.get('value', '')}

{context}

请进行深度分析。"""
        
        # 调用LLM（增加异常捕获与重试）
        max_retries = 3
        analysis_text = ""
        for attempt in range(max_retries):
            try:
                result = await self._model_client.create(
                    messages=[
                        self._system_message,
                        UserMessage(content=prompt, source=self.id.key)
                    ],
                    cancellation_token=ctx.cancellation_token
                )
                
                # 检查返回结果
                if result is None or not hasattr(result, 'content') or result.content is None:
                    logger.warning(f"LLM 返回空结果（尝试 {attempt + 1}/{max_retries}）: {message.paper_id}")
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        analysis_text = f"分析失败：LLM 返回空结果\n关键概念：无"
                        break
                
                # 提取关键概念并移除 <think> 标签
                analysis_text = self._remove_think_tags(result.content) if isinstance(result.content, str) else ""
                break  # 成功则退出重试
            except Exception as e:
                logger.error(f"LLM 调用异常（尝试 {attempt + 1}/{max_retries}）: {message.paper_id} - {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    analysis_text = f"分析失败：{str(e)[:100]}\n关键概念：无"
                    break
        key_concepts = []
        if "关键概念：" in analysis_text:
            concepts_str = analysis_text.split("关键概念：")[-1].strip()
            key_concepts = [c.strip() for c in concepts_str.split(',')[:5]]
        
        # 存入知识库
        doc_text = f"{message.title}\n{analysis_text}"
        embedding = self._embedding.encode_single(doc_text)
        self._chroma.upsert_if_changed(
            ids=[f"{message.paper_id}-analysis"],
            embeddings=[embedding],
            documents=[doc_text],
            metadatas=[{"title": message.title, "type": "analysis"}]
        )
        
        # 发布到评级Agent
        await self.publish_message(
            AnalysisData(
                paper_id=message.paper_id,
                title=message.title,
                analysis=analysis_text,
                key_concepts=key_concepts
            ),
            topic_id=TopicId("GraderAgent", source=self.id.key)
        )
        
        logger.success(f"分析完成: {message.paper_id}")

    def _remove_think_tags(self, text: str) -> str:
        """移除 <think>...</think> 标签及其内部内容（用于推理模型）"""
        import re
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

