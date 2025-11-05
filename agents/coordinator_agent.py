"""调度协调Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from utils.message_types import ReportData, ProcessingPlan, GradeData, GradeBatchData
from pathlib import Path
from datetime import datetime
from loguru import logger


@type_subscription(topic_type="CoordinatorAgent")
class CoordinatorAgent(RoutedAgent):
    """调度Agent - 统筹状态、汇总评级并保存报告"""
    
    def __init__(self):
        super().__init__("调度Agent")
        self._topic: str | None = None
        self._total_papers: int = 0
        self._grades: list[GradeData] = []
    
    @message_handler
    async def handle_plan(self, message: ProcessingPlan, ctx: MessageContext) -> None:
        """接收处理计划，记录主题与总量"""
        self._topic = message.topic
        self._total_papers = message.total_papers
        self._grades = []
        logger.info(f"接收处理计划：主题={self._topic}, 总量={self._total_papers}")
    
    @message_handler
    async def handle_grade(self, message: GradeData, ctx: MessageContext) -> None:
        """收集评级结果；当达到总量后触发撰写"""
        self._grades.append(message)
        logger.info(f"已收集评级 {len(self._grades)}/{self._total_papers}")
        
        if self._total_papers and len(self._grades) >= self._total_papers:
            topic = self._topic or "未知主题"
            logger.info("评级收集完成，触发撰写")
            await self.publish_message(
                GradeBatchData(topic=topic, grades=self._grades),
                topic_id=TopicId("WriterAgent", source=self.id.key)
            )
    
    @message_handler
    async def handle_report(self, message: ReportData, ctx: MessageContext) -> None:
        """处理报告数据"""
        logger.info("保存报告...")
        
        # 创建报告目录
        report_dir = Path("./cache/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{message.topic}.md"
        filepath = report_dir / filename
        
        # 写入报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(message.content)
            f.write("\n\n---\n\n## 参考文献\n\n")
            for ref in message.references:
                f.write(f"{ref}\n")
        
        logger.success(f"报告已保存: {filepath}")
        print(f"\n{'='*60}")
        print(f" 调研报告生成完成！")
        print(f" 报告路径: {filepath.absolute()}")
        print(f" 参考文献: {len(message.references)} 篇")
        print(f"{'='*60}\n")

