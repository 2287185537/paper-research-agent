# 基于 AutoGen 多智能体的论文调研报告生成系统

## 项目简介

这是一个基于 **AutoGen** 架构的智能论文调研系统，通过**多智能体协作**自动完成从论文检索、分析到报告撰写的全流程。系统采用模块化设计，支持分章写作、知识库检索增强（RAG）、风险评级、MCP 工具集成等高级特性。

### 核心特性

-  **智能体协作流程**：采集 → 摘要 → 分析 → 评级 → 撰写 → 装配 → 调度
-  **向量知识库**：基于 ChromaDB + Sentence-Transformers 的语义检索
-  **分章写作模式**：按目录结构逐章生成，每章独立 RAG 检索
-  **智能评级机制**：风险评分 + 人工审核双重把关
-  **MCP 工具支持**（可选）：集成外部工具辅助 ReAct 写作
-  **缓存与持久化**：论文搜索缓存、向量数据库持久化、报告归档
-  **多模型兼容**：支持 OpenAI 兼容 API（智谱 AI、DeepSeek、通义千问等）

---

## 系统架构

### 工作流程图

```
用户输入主题
    ↓
[CollectorAgent] 从 arXiv 采集论文
    ↓
[SummarizerAgent] 提取三要素（问题/方法/价值）并入库
    ↓
[AnalyzerAgent] 结合知识库进行深度分析并入库
    ↓
[GraderAgent] 风险评分 + 人工审核
    ↓
[CoordinatorAgent] 汇总评级结果
    ↓
[WriterAgent] 分章撰写（RAG 检索支持）
    ↓
[AssemblerAgent] 合并章节 + 去重引用 + 润色
    ↓
生成 Markdown 报告
```

### 智能体职责

| 智能体 | 职责 | 核心技术 |
|--------|------|----------|
| **CollectorAgent** | 论文采集 | arXiv API + 搜索缓存 |
| **SummarizerAgent** | 摘要提取 | LLM 提取三要素 + JSON 解析 |
| **AnalyzerAgent** | 深度分析 | RAG 检索 + 关键概念提取 |
| **GraderAgent** | 评级审核 | 风险评分 + 人工确认 |
| **WriterAgent** | 报告撰写 | 分章写作 + RAG + MCP 工具 |
| **AssemblerAgent** | 报告装配 | 章节合并 + 引用去重 + 润色 |
| **CoordinatorAgent** | 流程调度 | 状态管理 + 报告保存 |

---

## 项目结构

```
.
├── agents/                     # 智能体模块
│   ├── collector_agent.py      # 论文采集
│   ├── summarizer_agent.py     # 摘要提取
│   ├── analyzer_agent.py       # 深度分析
│   ├── grader_agent.py         # 评级审核
│   ├── writer_agent.py         # 报告撰写
│   ├── assembler_agent.py      # 报告装配
│   └── coordinator_agent.py    # 流程调度
│
├── workflows/                  # 工作流编排
│   └── sequential_workflow.py  # 顺序工作流
│
├── services/                   # 外部服务
│   ├── arxiv_service.py        # arXiv 论文检索
│   └── llm_client.py           # LLM 客户端（备用）
│
├── knowledge_base/             # 知识库管理
│   ├── chroma_manager.py       # ChromaDB 管理
│   └── embedding_service.py    # 嵌入模型服务
│
├── utils/                      # 工具模块
│   ├── message_types.py        # 消息协议定义
│   └── logger.py               # 日志配置
│
├── config/                     # 配置管理
│   └── settings.py             # Pydantic 配置类
│
├── cache/                      # 缓存目录
│   ├── chroma/                 # 向量数据库
│   ├── models/                 # 嵌入模型
│   ├── papers/                 # 论文搜索缓存
│   └── reports/                # 生成的报告
│
├── logs/                       # 日志文件
├── main.py                     # 主程序入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
├── autogenmcp.json.example     # MCP 配置示例
└── README.md                   # 本文档
```

---

## 快速开始

### 1. 环境要求

- **Python**: 3.12+（推荐 3.12）
- **操作系统**: Windows / macOS / Linux
- **API 密钥**: OpenAI 兼容 LLM API（智谱 AI / DeepSeek / 通义千问等）

### 2. 安装依赖

```bash
# 克隆项目
git clone <your-repo-url>
cd <project-directory>

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# LLM API 配置
API_KEY=your_api_key_here
BASE_URL=https://open.bigmodel.cn/api/paas/v4/  # 智谱 AI
MODEL_NAME=glm-4-flash

# 嵌入模型配置
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_CACHE_DIR=./cache/models

# ChromaDB 配置
CHROMA_PERSIST_DIR=./cache/chroma

# 工作流配置
RISK_THRESHOLD=4.0
MAX_PAPERS=50
MIN_PAPERS_FOR_REPORT=5

# 分章写作配置
WRITER_USE_SECTION_FLOW=true
SECTION_MIN_WORDS=3000
SECTION_DETAIL_LEVEL=详细
SECTION_RAG_TOP_K=5

# MCP 工具配置（可选）
WRITER_USE_MCP_TOOLS=false
AUTOGEN_MCP_CONFIG_PATH=./autogenmcp.json
```

### 4. 运行系统

```bash
python main.py
```

按提示输入研究主题（如：`transformer`、`multi-agent systems`），系统将自动完成以下流程：

1. 从 arXiv 检索相关论文
2. 提取论文三要素并入知识库
3. 结合知识库进行深度分析
4. 风险评级与人工审核
5. 分章撰写调研报告
6. 合并章节并生成最终报告

生成的报告保存在 `./cache/reports/` 目录。

---

## 核心配置说明

### 配置文件：`config/settings.py`

所有配置均通过 **Pydantic Settings** 管理，支持环境变量覆盖。

#### LLM 配置

```python
api_key: str                    # API 密钥（必填）
base_url: str                   # API 基础 URL
model_name: str                 # 模型名称（如 glm-4-flash）
```

#### 嵌入模型配置

```python
embedding_model: str            # 模型名称（默认：paraphrase-multilingual-MiniLM-L12-v2）
embedding_cache_dir: str        # 模型缓存目录
```

#### 工作流配置

```python
risk_threshold: float           # 风险阈值（≥此值触发人工审核）
max_papers: int                 # 最大采集论文数
min_papers_for_report: int      # 生成报告所需最少通过论文数
```

#### 分章写作配置

```python
writer_use_section_flow: bool   # 是否启用分章写作（推荐 true）
section_outline: List[str]      # 报告目录结构
section_rag_top_k: int          # 每章 RAG 召回数量
section_min_words: int          # 每章最少字数
section_detail_level: str       # 详细程度（简要/详细/深入）
```

默认目录结构：
1. 引言与背景
2. 理论基础与范式转变
3. 任务视角（Task Domains）
4. 环境与框架（Environments & Frameworks）
5. 挑战与未来方向（Challenges & Future Directions）
6. 结论

#### MCP 工具配置（可选）

```python
writer_use_mcp_tools: bool      # 是否启用 MCP 工具
autogen_mcp_config_path: str    # MCP 配置文件路径
```

**MCP 配置示例**（`autogenmcp.json`）：

```json
{
  "servers": [
    {
      "name": "tavily-search",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-tavily"],
      "env": {
        "TAVILY_API_KEY": "${TAVILY_API_KEY}"
      }
    }
  ]
}
```

---

## 技术栈

### 核心框架

- **AutoGen Core 0.4.0**: 新一代多智能体框架
- **AutoGen Extensions 0.4.0**: OpenAI 客户端扩展

### 知识库与向量搜索

- **ChromaDB 0.5.3**: 轻量级向量数据库
- **Sentence-Transformers 3.0.1**: 多语言嵌入模型
- **PyTorch**: 深度学习框架

### 外部服务

- **arXiv**: 论文检索 API
- **OpenAI SDK**: LLM 调用（兼容多家厂商）

### 工具库

- **Pydantic**: 配置与数据验证
- **Loguru**: 优雅的日志库
- **Tenacity**: 重试机制
- **HTTPX**: 异步 HTTP 客户端

---

## 高级特性

### 1. 分章写作流程

系统支持按章节逐步撰写报告，每章独立进行：

1. **章节规划**：基于前文与知识库提取关键词
2. **RAG 检索**：检索前文章节、论文摘要、深度分析
3. **内容生成**：根据检索结果生成章节正文
4. **自审修订**：术语统一、事实核验、去重
5. **入库**：章节内容入库供后续章节参考

**优势**：
- 每章有独立上下文，避免超长文本截断
- 前文章节可被后续章节检索引用
- 支持 MCP 工具在写作过程中调用外部资源

### 2. 知识库检索增强（RAG）

系统在多个阶段使用 RAG：

| 阶段 | 检索内容 | 用途 |
|------|----------|------|
| **分析阶段** | 相似论文摘要 | 提供上下文辅助深度分析 |
| **撰写阶段** | 前文章节 + 论文摘要 + 深度分析 | 章节内容生成 |

**去重机制**：
- 仅在内容变化时入库（`upsert_if_changed`）
- 避免重复写入，提升性能

### 3. 智能评级机制

**风险评分规则**：
- 分析长度 < 100 字：+3.0
- 关键概念 < 2 个：+2.0
- 包含失败标记：+5.0

**人工审核**：
- 评分 ≥ 阈值（默认 4.0）触发人工确认
- 显示论文标题、评分、分析摘要
- 用户可选择通过/拒绝

### 4. MCP 工具集成（可选）

系统支持在 **WriterAgent** 撰写阶段调用 MCP 工具（如网络搜索、数据库查询等），实现 **ReAct** 循环：

1. 模型生成内容并发起工具调用
2. 执行工具并返回结果
3. 模型基于结果继续生成
4. 重复直至生成完成（最多 10 轮）

**支持的 MCP 服务器**：
- Tavily 搜索
- 文件系统操作
- 数据库查询
- 自定义工具

### 5. 报告装配与润色

**AssemblerAgent** 负责最终报告生成：

1. **章节合并**：按目录顺序拼接章节
2. **引用去重**：保持出现顺序，去除重复引用
3. **后处理**：
   - 移除技术审校标记
   - 清理 AI 机械衔接词（"首先、其次、总之"等）
   - 减少过度加粗（每段保留 2-3 个）
   - 清理重复空行
4. **终稿润色**：
   - 语言优化（消除机械风格）
   - 逻辑连贯（章节承上启下）
   - 排版美化（小标题、段落长度）
   - 学术规范（引用、术语、数据）

---

## 使用示例

### 基础用法

```bash
python main.py
# 输入主题：transformer
```

### 高级用法：启用 MCP 工具

1. 配置 `.env`：
   ```bash
   WRITER_USE_MCP_TOOLS=true
   AUTOGEN_MCP_CONFIG_PATH=./autogenmcp.json
   ```

2. 配置 `autogenmcp.json`：
   ```json
   {
     "servers": [
       {
         "name": "tavily-search",
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-tavily"],
         "env": {
           "TAVILY_API_KEY": "your_tavily_key"
         }
       }
     ]
   }
   ```

3. 运行系统（写作阶段将自动调用 Tavily 搜索工具）

### 自定义章节目录

修改 `config/settings.py`：

```python
section_outline: List[str] = [
    "研究背景与动机",
    "核心技术与方法",
    "实验结果与分析",
    "应用案例与落地",
    "挑战与未来方向",
    "总结"
]
```

---

## 开发指南

### 添加新智能体

1. 在 `agents/` 下创建 `your_agent.py`：

```python
from autogen_core import RoutedAgent, message_handler, type_subscription
from utils.message_types import YourMessageType

@type_subscription(topic_type="YourAgent")
class YourAgent(RoutedAgent):
    def __init__(self):
        super().__init__("您的智能体")
    
    @message_handler
    async def handle_message(self, message: YourMessageType, ctx: MessageContext):
        # 处理逻辑
        pass
```

2. 在 `workflows/sequential_workflow.py` 注册：

```python
await YourAgent.register(
    self.runtime,
    type="YourAgent",
    factory=lambda: YourAgent()
)
```

3. 在 `utils/message_types.py` 定义消息类型：

```python
@dataclass
class YourMessageType:
    field1: str
    field2: int
```

### 添加新服务

在 `services/` 下创建服务类，参考 `arxiv_service.py` 实现缓存机制。

### 日志配置

系统使用 **Loguru** 进行日志管理：
- **控制台**：INFO 级别，彩色输出
- **文件**：DEBUG 级别，按日期轮转，保留 30 天

自定义日志：

```python
from loguru import logger

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
logger.success("成功日志")
```

---

## 常见问题

### 1. 嵌入模型加载失败

**问题**：首次运行时下载模型较慢或失败。

**解决方案**：
- 手动下载模型到 `./cache/models/`
- 使用国内镜像：`export HF_ENDPOINT=https://hf-mirror.com`

### 2. LLM API 调用失败

**问题**：API 密钥错误或网络问题。

**解决方案**：
- 检查 `.env` 中的 `API_KEY` 和 `BASE_URL`
- 确认 API 余额充足
- 查看 `./logs/` 中的详细错误日志

### 3. 报告生成质量不佳

**问题**：报告内容重复、逻辑混乱。

**解决方案**：
- 增加 `SECTION_MIN_WORDS` 提升章节长度
- 调整 `SECTION_RAG_TOP_K` 增加检索数量
- 修改 `section_outline` 优化目录结构
- 使用更强大的 LLM 模型（如 GPT-4、Claude）

### 4. ChromaDB 持久化问题

**问题**：重启后知识库丢失。

**解决方案**：
- 确保 `CHROMA_PERSIST_DIR` 路径正确
- 检查目录写入权限
- 不要在运行时删除 `./cache/chroma/` 目录

### 5. MCP 工具调用失败

**问题**：工具未找到或执行错误。

**解决方案**：
- 确认 Node.js 已安装（`npx` 命令可用）
- 检查 `autogenmcp.json` 配置正确
- 查看日志中的工具调用详情
- 测试 MCP 服务器独立运行：`npx -y @modelcontextprotocol/server-tavily`

---

## 性能优化

### 1. 缓存策略

- **论文搜索缓存**：基于查询 MD5 缓存，避免重复检索
- **向量数据库缓存**：仅在内容变化时写入
- **嵌入模型缓存**：本地优先加载，避免重复下载

### 2. 并发优化

- 当前采用 **SingleThreadedAgentRuntime**，适合小规模任务
- 可升级为 **MultiAgentRuntime** 实现并发处理

### 3. 批量处理

- **批量编码**：嵌入服务支持批量文本编码（默认 batch_size=32）
- **批量入库**：ChromaDB 支持批量 upsert

---

## 安全与合规

### 敏感信息管理

- API 密钥存储在 `.env` 文件（已加入 `.gitignore`）
- 提供 `.env.example` 作为模板
- 禁止在代码中硬编码密钥

### 数据隐私

- 论文数据仅用于学术研究
- 本地缓存，无数据上传
- 知识库可定期清理（删除 `./cache/chroma/`）

### API 调用控制

- 内置重试机制（最多 3 次，指数退避）
- 支持自定义 `timeout` 和 `max_retries`
- 建议设置 API 调用频率限制




