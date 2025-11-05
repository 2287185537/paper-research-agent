"""论文采集Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from utils.message_types import PaperRequest, PaperData, ProcessingPlan
from services.arxiv_service import ArxivService
from loguru import logger


@type_subscription(topic_type="CollectorAgent")
class CollectorAgent(RoutedAgent):
    """论文采集Agent"""
    
    def __init__(self, arxiv_service: ArxivService):
        super().__init__("论文采集Agent")
        self.arxiv_service = arxiv_service
    
    @message_handler
    async def handle_request(self, message: PaperRequest, ctx: MessageContext) -> None:
        """处理论文请求"""
        logger.info(f"开始采集论文: {message.keyword}")
        
        # 搜索论文
        papers = self.arxiv_service.search_papers(message.keyword, message.max_count)
        
        # 通知协调器本批次处理计划（总量与主题）
        await self.publish_message(
            ProcessingPlan(topic=message.keyword, total_papers=len(papers)),
            topic_id=TopicId("CoordinatorAgent", source=self.id.key)
        )

        # 发布到摘要Agent
        await self.publish_message(
            PaperData(papers=papers),
            topic_id=TopicId("SummarizerAgent", source=self.id.key)
        )
        
        logger.success(f"论文采集完成，共 {len(papers)} 篇")

