"""论文评级Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from utils.message_types import AnalysisData, GradeData
from config.settings import settings
from loguru import logger


@type_subscription(topic_type="GraderAgent")
class GraderAgent(RoutedAgent):
    """评级Agent - 评分和人工审核"""
    
    def __init__(self):
        super().__init__("评级Agent")
    
    @message_handler
    async def handle_analysis(self, message: AnalysisData, ctx: MessageContext) -> None:
        """处理分析数据"""
        logger.info(f"评级论文: {message.title[:30]}...")
        
        # 计算风险评分（基于分析长度和关键概念数量）
        risk_score = 0.0
        if len(message.analysis) < 100:
            risk_score += 3.0
        if len(message.key_concepts) < 2:
            risk_score += 2.0
        if "解析失败" in message.analysis or "API调用失败" in message.analysis or "分析失败" in message.analysis:
            risk_score += 5.0
        
        approved = True
        
        # 人工审核
        if risk_score >= settings.risk_threshold:
            logger.warning(f"检测到高风险内容 (评分: {risk_score})")
            print(f"\n{'='*60}")
            print(f"论文: {message.title}")
            print(f"风险评分: {risk_score}")
            print(f"分析摘要: {message.analysis[:200]}...")
            print(f"{'='*60}")
            
            response = input("是否批准继续? (yes/no): ").lower().strip()
            approved = response in ['yes', 'y', '是']
            
            if not approved:
                logger.info("用户拒绝，跳过该论文")
                return
        
        # 发布到协调Agent（汇总后再触发撰写）
        await self.publish_message(
            GradeData(
                paper_id=message.paper_id,
                title=message.title,
                risk_score=risk_score,
                approved=approved,
                analysis=message.analysis
            ),
            topic_id=TopicId("CoordinatorAgent", source=self.id.key)
        )
        
        logger.success(f"评级完成: {message.paper_id} (评分: {risk_score})")

