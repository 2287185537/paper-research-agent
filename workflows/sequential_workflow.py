"""顺序工作流编排"""
from autogen_core import SingleThreadedAgentRuntime, TopicId
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agents.collector_agent import CollectorAgent
from agents.summarizer_agent import SummarizerAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.grader_agent import GraderAgent
from agents.writer_agent import WriterAgent
from agents.assembler_agent import AssemblerAgent
from agents.coordinator_agent import CoordinatorAgent
from services.arxiv_service import ArxivService
from knowledge_base.chroma_manager import ChromaManager
from knowledge_base.embedding_service import EmbeddingService
from utils.message_types import PaperRequest
from config.settings import settings
from loguru import logger


class ResearchWorkflow:
    """论文调研工作流"""
    
    def __init__(self):
        self.runtime = SingleThreadedAgentRuntime()
        
        # 初始化模型客户端
        logger.info("初始化LLM客户端")
        self.model_client = OpenAIChatCompletionClient(
            model=settings.model_name,
            api_key=settings.api_key,
            base_url=settings.base_url,
            model_info={
                "vision": False,
                "function_calling": False,
                "json_output": False,
                "family": "unknown",
                "structured_output": False,
            }
        )
        
        # 初始化服务
        logger.info("初始化服务")
        self.arxiv_service = ArxivService()
        self.embedding_service = EmbeddingService(
            settings.embedding_model,
            settings.embedding_cache_dir
        )
        self.chroma_manager = ChromaManager(settings.chroma_persist_dir)
    
    async def setup(self, topic: str):
        """注册所有Agent"""
        logger.info("注册Agent...")
        
        # 注册采集Agent
        await CollectorAgent.register(
            self.runtime,
            type="CollectorAgent",
            factory=lambda: CollectorAgent(self.arxiv_service)
        )
        
        # 注册摘要Agent
        await SummarizerAgent.register(
            self.runtime,
            type="SummarizerAgent",
            factory=lambda: SummarizerAgent(self.model_client, self.chroma_manager, self.embedding_service)
        )
        
        # 注册分析Agent
        await AnalyzerAgent.register(
            self.runtime,
            type="AnalyzerAgent",
            factory=lambda: AnalyzerAgent(
                self.model_client,
                self.chroma_manager,
                self.embedding_service
            )
        )
        
        # 注册评级Agent
        await GraderAgent.register(
            self.runtime,
            type="GraderAgent",
            factory=lambda: GraderAgent()
        )
        
        # 注册撰写Agent
        await WriterAgent.register(
            self.runtime,
            type="WriterAgent",
            factory=lambda: WriterAgent(self.model_client, topic, self.chroma_manager, self.embedding_service)
        )
        
        # 注册装配Agent（注入模型用于终稿润色）
        await AssemblerAgent.register(
            self.runtime,
            type="AssemblerAgent",
            factory=lambda: AssemblerAgent(self.model_client)
        )
        
        # 注册调度Agent
        await CoordinatorAgent.register(
            self.runtime,
            type="CoordinatorAgent",
            factory=lambda: CoordinatorAgent()
        )
        
        logger.success("所有Agent注册完成")
    
    async def run(self, topic: str):
        """执行工作流"""
        logger.info(f"启动工作流: {topic}")
        
        # 设置Agent
        await self.setup(topic)
        
        # 启动运行时
        self.runtime.start()
        
        # 发布初始任务
        await self.runtime.publish_message(
            PaperRequest(keyword=topic, max_count=settings.max_papers),
            topic_id=TopicId("CollectorAgent", source="user")
        )
        
        # 等待完成
        await self.runtime.stop_when_idle()
        
        # 清理资源（当前客户端无需显式关闭）
        
        logger.success("工作流执行完成")

