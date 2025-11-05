"""Agent间消息协议定义"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class PaperRequest:
    """论文请求消息"""
    keyword: str  # 搜索关键词
    max_count: int  # 最大论文数


@dataclass
class PaperData:
    """论文数据消息"""
    papers: List[Dict]  # 论文列表: {id, title, authors, abstract, url, published}


@dataclass
class SummaryData:
    """摘要数据消息"""
    paper_id: str
    title: str
    summary: Dict  # {research_problem, method, value}


@dataclass
class AnalysisData:
    """分析数据消息"""
    paper_id: str
    title: str
    analysis: str  # 分析内容
    key_concepts: List[str]  # 关键概念


@dataclass
class GradeData:
    """评级数据消息"""
    paper_id: str
    title: str
    risk_score: float  # 风险评分
    approved: bool  # 是否通过审核
    analysis: str  # 分析内容


@dataclass
class ReportData:
    """报告数据消息"""
    topic: str  # 研究主题
    content: str  # 报告内容
    references: List[str]  # 参考文献


@dataclass
class ProcessingPlan:
    """处理计划（用于Coordinator掌握总量与主题）"""
    topic: str  # 研究主题
    total_papers: int  # 需要处理的论文总数


@dataclass
class GradeBatchData:
    """批量评级结果（Coordinator 收齐后一次性发送给 Writer）"""
    topic: str  # 研究主题
    grades: List[GradeData]  # 完整评级结果列表（可包含未通过）


@dataclass
class SectionPlan:
    """章节计划（可选，用于分章写作）"""
    topic: str
    sections: List[str]


@dataclass
class SectionDraft:
    """章节草稿（可选，留给装配/质检Agent使用）"""
    topic: str
    run_id: str
    section_id: str
    content: str
    citations: List[str]


@dataclass
class AssembleRequest:
    """装配请求：通知装配Agent开始合并草稿并输出最终报告"""
    topic: str
    run_id: str
    sections: List[str]
