"""论文摘要Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from utils.message_types import PaperData, SummaryData
from loguru import logger
from knowledge_base.chroma_manager import ChromaManager
from knowledge_base.embedding_service import EmbeddingService


@type_subscription(topic_type="SummarizerAgent")
class SummarizerAgent(RoutedAgent):
    """摘要Agent - 提取论文三要素"""
    
    def __init__(self, model_client: ChatCompletionClient, chroma_manager: ChromaManager, embedding_service: EmbeddingService):
        super().__init__("摘要Agent")
        self._model_client = model_client
        self._chroma = chroma_manager
        self._embedding = embedding_service
        self._system_message = SystemMessage(
            content="""你是论文分析专家。请从论文标题和摘要中提取以下三要素，并以严格的 JSON 对象返回：
1. research_problem: 研究的核心问题（一句话概括）
2. method: 使用的方法或技术（一句话概括）
3. value: 研究的价值和贡献（一句话概括）

必须遵循：
- 仅输出一个严格的 JSON 对象，不要输出任何额外文字、解释、提示语；
- 不要使用反引号、不要使用代码块标记（如 ```json）；
- 使用双引号作为键和值的引号；
- 键名必须为 research_problem、method、value；
- 不要在 JSON 外部添加任何字符（包括前后空行）。

返回格式示例（仅供结构参考，请直接输出 JSON 对象本身，不要额外说明）：
{
  "research_problem": "如何提升Transformer模型的效率",
  "method": "提出了注意力机制优化算法",
  "value": "将推理速度提升3倍，降低50%内存占用"
}
"""
        )
    
    @message_handler
    async def handle_papers(self, message: PaperData, ctx: MessageContext) -> None:
        """处理论文数据"""
        logger.info(f"开始摘要 {len(message.papers)} 篇论文")
        
        for paper in message.papers:
            # 构建提示词
            prompt = f"论文标题：{paper['title']}\n\n摘要：{paper['abstract']}"
            
            # 调用LLM（增加异常捕获与重试）
            max_retries = 3
            summary = None
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
                        logger.warning(f"LLM 返回空结果（尝试 {attempt + 1}/{max_retries}）: {paper['id']}")
                        if attempt < max_retries - 1:
                            import asyncio
                            await asyncio.sleep(2 ** attempt)  # 指数退避
                            continue
                        else:
                            raise ValueError("LLM 返回结果为空")
                    
                    # 解析结果（先清理 <think> 标签）
                    import json
                    cleaned_content = self._remove_think_tags(result.content) if isinstance(result.content, str) else "{}"
                    try:
                        summary = json.loads(cleaned_content)
                        break  # 成功则退出重试
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 解析失败（尝试 {attempt + 1}/{max_retries}）: {e}\n原始内容: {cleaned_content[:200]}")
                        if attempt < max_retries - 1:
                            import asyncio
                            await asyncio.sleep(2 ** attempt)
                            continue
                        else:
                            summary = {
                                "research_problem": "JSON解析失败",
                                "method": "JSON解析失败",
                                "value": "JSON解析失败"
                            }
                            break
                except Exception as e:
                    logger.error(f"LLM 调用异常（尝试 {attempt + 1}/{max_retries}）: {paper['id']} - {e}")
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        summary = {
                            "research_problem": f"API调用失败: {str(e)[:50]}",
                            "method": "API调用失败",
                            "value": "API调用失败"
                        }
                        break
            
            # 确保 summary 不为空
            if summary is None:
                summary = {
                    "research_problem": "处理失败",
                    "method": "处理失败",
                    "value": "处理失败"
                }
            
            # 将摘要写入知识库（先入库以便后续论文可检索到）
            try:
                brief = f"{paper['title']}\n问题:{summary.get('research_problem','')} 方法:{summary.get('method','')} 价值:{summary.get('value','')}"
                emb = self._embedding.encode_single(brief)
                self._chroma.upsert_if_changed(
                    ids=[f"{paper['id']}-summary"],
                    embeddings=[emb],
                    documents=[brief],
                    metadatas=[{"title": paper['title'], "type": "summary"}]
                )
            except Exception as e:
                logger.warning(f"摘要入库失败: {paper['id']} - {e}")
            
            # 发布到分析Agent
            await self.publish_message(
                SummaryData(
                    paper_id=paper['id'],
                    title=paper['title'],
                    summary=summary
                ),
                topic_id=TopicId("AnalyzerAgent", source=self.id.key)
            )
        
        logger.success("论文摘要完成")

    def _remove_think_tags(self, text: str) -> str:
        """移除 <think>...</think> 标签及其内部内容（用于推理模型）"""
        import re
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

