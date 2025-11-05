"""配置管理"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """系统配置"""
    
    # LLM API配置（通用）
    api_key: str = Field(..., description="LLM API密钥")
    base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        description="LLM API基础URL"
    )
    model_name: str = Field(default="glm-4-flash", description="使用的模型名称")
    
    # 嵌入模型配置
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="嵌入模型名称"
    )
    embedding_cache_dir: str = Field(
        default="./cache/models",
        description="嵌入模型缓存目录"
    )
    
    # ChromaDB配置
    chroma_persist_dir: str = Field(
        default="./cache/chroma",
        description="ChromaDB持久化目录"
    )
    
    # 工作流配置
    risk_threshold: float = Field(default=4.0, description="风控阈值")
    max_papers: int = Field(default=50, description="最大论文数量")
    min_papers_for_report: int = Field(default=5, description="生成报告所需最少通过论文数")

    # 分章写作与RAG配置
    writer_use_section_flow: bool = Field(default=True, description="是否启用分章写作流程")
    section_outline: List[str] = Field(
        default_factory=lambda: [
            "引言与背景",
            "理论基础与范式转变",
            "任务视角（Task Domains）",
            "环境与框架（Environments & Frameworks）",
            "挑战与未来方向（Challenges & Future Directions）",
            "结论",
        ],
        description="报告章节目录"
    )
    section_rag_top_k: int = Field(default=5, description="章节生成时RAG召回条目数")
    section_db_persist: bool = Field(default=True, description="是否保留本次临时章节向量入库")

    # MCP工具与ReAct写作（可选）
    writer_use_mcp_tools: bool = Field(default=False, description="是否启用MCP工具辅助写作")
    autogen_mcp_config_path: str = Field(default="./autogenmcp.json", description="MCP服务器配置文件路径")
    
    # 章节写作详细度
    section_min_words: int = Field(default=3000, description="每章节目标最少字数（中文）")
    section_detail_level: str = Field(default="详细", description="章节详细程度：简要/详细/深入")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


# 全局配置实例
settings = Settings()

