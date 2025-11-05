# 系统架构文档

## 整体架构

本系统采用**多智能体协作架构**，基于 AutoGen 0.4 框架实现。每个智能体负责特定任务，通过消息传递实现协作。

```
┌─────────────────────────────────────────────────────────────┐
│                         用户交互层                           │
│                       (main.py)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       工作流编排层                           │
│                (ResearchWorkflow)                           │
│                 - Agent 注册管理                             │
│                 - 运行时控制                                 │
│                 - 消息路由                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       智能体层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Collector  │  │ Summarizer  │  │  Analyzer   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Grader    │  │   Writer    │  │  Assembler  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐                                            │
│  │ Coordinator │                                            │
│  └─────────────┘                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       服务层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ArxivService │  │  LLMClient   │  │ ChromaManager│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                           │
│  │EmbeddingServ │                                           │
│  └──────────────┘                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       存储层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ChromaDB     │  │  Cache       │  │    Logs      │      │
│  │ (向量数据库)  │  │  (论文/模型)  │  │  (运行日志)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流图

### 完整工作流数据流

```
用户输入主题
    ↓
[1. 论文采集阶段]
CollectorAgent
    ├─> 调用 ArxivService 搜索论文
    ├─> 缓存搜索结果到 cache/papers/
    ├─> 发布 ProcessingPlan → CoordinatorAgent
    └─> 发布 PaperData → SummarizerAgent

[2. 摘要提取阶段]
SummarizerAgent
    ├─> 调用 LLM 提取三要素（问题/方法/价值）
    ├─> 将摘要入库 ChromaDB (type=summary)
    └─> 发布 SummaryData → AnalyzerAgent

[3. 深度分析阶段]
AnalyzerAgent
    ├─> 从 ChromaDB 检索相似论文
    ├─> 调用 LLM 进行深度分析
    ├─> 提取关键概念
    ├─> 将分析入库 ChromaDB (type=analysis)
    └─> 发布 AnalysisData → GraderAgent

[4. 评级审核阶段]
GraderAgent
    ├─> 计算风险评分
    ├─> 触发人工审核（如需）
    └─> 发布 GradeData → CoordinatorAgent

[5. 汇总调度阶段]
CoordinatorAgent
    ├─> 收集所有评级结果
    ├─> 等待收集完成
    └─> 发布 GradeBatchData → WriterAgent

[6. 报告撰写阶段]
WriterAgent
    ├─> 按章节循环撰写
    │   ├─> 规划章节来源
    │   ├─> RAG 检索（前文章节 + 摘要 + 分析）
    │   ├─> 调用 LLM 生成章节（可选 MCP 工具）
    │   ├─> 自审修订
    │   ├─> 将章节入库 ChromaDB (type=section)
    │   └─> 发布 SectionDraft → AssemblerAgent
    └─> 发布 AssembleRequest → AssemblerAgent

[7. 报告装配阶段]
AssemblerAgent
    ├─> 收集所有章节草稿
    ├─> 按目录顺序合并
    ├─> 引用去重
    ├─> 后处理（清理机械表达、优化排版）
    ├─> 终稿润色（调用 LLM）
    └─> 发布 ReportData → CoordinatorAgent

[8. 保存报告阶段]
CoordinatorAgent
    ├─> 保存报告到 cache/reports/
    └─> 输出完成信息
```

---

## 核心组件详解

### 1. 智能体层 (Agents)

#### CollectorAgent (论文采集)
- **输入**: `PaperRequest(keyword, max_count)`
- **输出**: `PaperData(papers)`, `ProcessingPlan(topic, total_papers)`
- **职责**:
  - 调用 arXiv API 搜索论文
  - 基于查询 MD5 缓存结果
  - 通知协调器处理计划

#### SummarizerAgent (摘要提取)
- **输入**: `PaperData(papers)`
- **输出**: `SummaryData(paper_id, title, summary)`
- **职责**:
  - 调用 LLM 提取三要素（JSON 格式）
  - 处理 API 失败和 JSON 解析异常
  - 将摘要入库供后续检索

#### AnalyzerAgent (深度分析)
- **输入**: `SummaryData`
- **输出**: `AnalysisData(paper_id, title, analysis, key_concepts)`
- **职责**:
  - 检索相似论文作为上下文
  - 调用 LLM 进行深度分析
  - 提取 3-5 个关键概念
  - 将分析结果入库

#### GraderAgent (评级审核)
- **输入**: `AnalysisData`
- **输出**: `GradeData(paper_id, title, risk_score, approved, analysis)`
- **职责**:
  - 计算风险评分（基于分析长度、概念数量、失败标记）
  - 触发人工审核（评分 ≥ 阈值）
  - 发布评级结果

**风险评分规则**:
```python
risk_score = 0.0
if len(analysis) < 100: risk_score += 3.0
if len(key_concepts) < 2: risk_score += 2.0
if "失败" in analysis: risk_score += 5.0
```

#### WriterAgent (报告撰写)
- **输入**: `GradeBatchData(topic, grades)`
- **输出**: `SectionDraft`, `AssembleRequest`
- **职责**:
  - 按章节循环撰写（如启用 `writer_use_section_flow`）
  - RAG 检索前文章节、论文摘要、深度分析
  - 调用 LLM 生成章节（可选 MCP 工具 ReAct）
  - 自审修订（术语统一、事实核验）
  - 将章节入库供后续章节引用

**分章写作流程**:
```python
for section in section_outline:
    # 1. 规划章节来源
    plan = await _plan_section_sources(section)
    
    # 2. RAG 检索
    prev_docs = chroma.retrieve(where={"run_id": run_id})
    kb_sum = chroma.retrieve(where={"type": "summary"})
    kb_ana = chroma.retrieve(where={"type": "analysis"})
    
    # 3. 生成章节（可选 MCP 工具）
    content = await llm.create(messages, tools=mcp_tools)
    
    # 4. 自审修订
    content = await llm.create(revise_prompt)
    
    # 5. 入库
    chroma.upsert(section_content, metadata={"type": "section"})
    
    # 6. 发布草稿
    publish(SectionDraft)
```

#### AssemblerAgent (报告装配)
- **输入**: `SectionDraft`, `AssembleRequest`
- **输出**: `ReportData(topic, content, references)`
- **职责**:
  - 收集所有章节草稿
  - 按目录顺序合并
  - 引用去重（保持出现顺序）
  - 后处理：清理机械表达、优化排版
  - 终稿润色（调用 LLM）

**后处理规则**:
- 移除技术审校标记
- 清理 AI 衔接词（"首先、其次、总之"等）
- 限制加粗数量（每段最多 3 个）
- 清理重复空行

#### CoordinatorAgent (流程调度)
- **输入**: `ProcessingPlan`, `GradeData`, `ReportData`
- **输出**: `GradeBatchData`
- **职责**:
  - 记录主题与论文总量
  - 收集所有评级结果
  - 触发撰写（收集完成后）
  - 保存最终报告

---

### 2. 服务层 (Services)

#### ArxivService
- **功能**: 论文检索与缓存
- **缓存策略**: 基于查询 + 数量的 MD5 哈希
- **缓存位置**: `cache/papers/search_{md5}.json`

#### ChromaManager
- **功能**: 向量数据库管理
- **集合**: `paper_knowledge`
- **文档类型**:
  - `summary`: 论文摘要三要素
  - `analysis`: 深度分析结果
  - `section`: 章节内容（可选持久化）
- **核心方法**:
  - `add_papers`: 批量添加
  - `upsert_if_changed`: 去重写入
  - `retrieve_similar`: 语义检索
  - `get_documents_by_ids`: 批量查询

#### EmbeddingService
- **功能**: 文本嵌入编码
- **模型**: Sentence-Transformers（多语言支持）
- **加载策略**: 本地优先 → 在线下载
- **缓存结构**: HuggingFace 标准格式（`models--{org}--{name}`）

---

### 3. 消息协议 (Message Types)

所有智能体间通信通过 **Dataclass** 定义的消息类型实现：

```python
@dataclass
class PaperRequest:
    keyword: str
    max_count: int

@dataclass
class PaperData:
    papers: List[Dict]  # {id, title, authors, abstract, url, published}

@dataclass
class SummaryData:
    paper_id: str
    title: str
    summary: Dict  # {research_problem, method, value}

@dataclass
class AnalysisData:
    paper_id: str
    title: str
    analysis: str
    key_concepts: List[str]

@dataclass
class GradeData:
    paper_id: str
    title: str
    risk_score: float
    approved: bool
    analysis: str

@dataclass
class GradeBatchData:
    topic: str
    grades: List[GradeData]

@dataclass
class SectionDraft:
    topic: str
    run_id: str
    section_id: str
    content: str
    citations: List[str]

@dataclass
class AssembleRequest:
    topic: str
    run_id: str
    sections: List[str]

@dataclass
class ReportData:
    topic: str
    content: str
    references: List[str]
```

---

## 扩展性设计

### 添加新智能体

1. 定义消息类型（`utils/message_types.py`）
2. 实现智能体类（`agents/your_agent.py`）
3. 注册到工作流（`workflows/sequential_workflow.py`）

### 切换 LLM 提供商

修改 `.env` 配置即可：

```bash
# DeepSeek
BASE_URL=https://api.deepseek.com/v1/
MODEL_NAME=deepseek-chat

# 通义千问
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/
MODEL_NAME=qwen-plus
```

### 集成新数据源

可以参考 `ArxivService` 实现新的服务类，支持：
- PubMed（医学论文）
- Google Scholar（综合学术）
- IEEE Xplore（工程论文）
---

## 安全与合规

### API 调用控制
- 重试机制：最多 3 次，指数退避
- 超时控制：默认 60 秒
- 错误处理：捕获所有异常并记录日志

### 数据隐私
- 本地存储：所有数据保存在 `cache/` 目录
- 无数据上传：不向第三方发送用户数据
- 可清理：删除 `cache/` 即可清空所有数据

### 敏感信息管理
- API 密钥：仅存储在 `.env` 文件（已加入 `.gitignore`）
- 日志脱敏：不记录完整 API 密钥
- 环境变量：支持 `${VAR}` 占位符

---


