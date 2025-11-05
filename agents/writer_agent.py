"""报告撰写Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
)
from utils.message_types import GradeData, ReportData, GradeBatchData, SectionDraft, AssembleRequest
from config.settings import settings
from knowledge_base.chroma_manager import ChromaManager
from knowledge_base.embedding_service import EmbeddingService
from datetime import datetime
import uuid
from loguru import logger
from typing import List
import json
import importlib


@type_subscription(topic_type="WriterAgent")
class WriterAgent(RoutedAgent):
    """撰写Agent - 生成调研报告"""
    
    def __init__(self, model_client: ChatCompletionClient, topic: str, chroma_manager: ChromaManager, embedding_service: EmbeddingService):
        super().__init__("撰写Agent")
        self._model_client = model_client
        self._topic = topic
        self._chroma = chroma_manager
        self._embedding = embedding_service
        self._approved_papers: List[GradeData] = []
        self._system_message = SystemMessage(
            content="""你是科研报告撰写专家。请严格按照以下目录结构撰写面向研究者的调研报告：

# 标题：{主题}领域调研报告

## 引言与背景
- 概述研究动机、应用场景与问题重要性；
- 简述研究现状与数据/任务规模变化趋势；
- 明确报告范围与不在范围内的内容。

## 理论基础与范式转变
- 澄清关键术语与定义，给出必要公式或概念图示；
- 总结从传统范式到新范式（如 Agentic）的迁移路径与原因；
- 强调与邻近领域（如RL/MARL/AutoML/RAG/Tool-Use）的边界与联系。

## 任务视角（Task Domains）
- 以任务划分小节：数据集/环境、评测指标、典型难点；
- 每个任务呈现代表性方法与可复现证据（指标、设置）。

## 环境与框架（Environments & Frameworks）
- 列举主流环境/基准/工具链（版本、特性、限制、可获得性）；
- 对比其适用任务与评测覆盖，指出缺口。

## 挑战与未来方向（Challenges & Future Directions）
- 以要点列出当前瓶颈（数据、评测、可复现性、安全与合规、成本等）；
- 给出3–5条可验证的研究计划（含指标、预期改进、风险）。

## 结论
- 总结关键洞见与实践建议，指出落地路径与优先级。

写作要求：
- 保持事实与证据导向；必要时在正文处使用[编号]进行内联引用；
- 避免空洞表述与重复；尽量给出现成指标或可复现设置；
- 文末将参考文献统一汇总（编号与正文一致）。"""
        )

        # 分章写作专用提示：仅输出正文，禁止输出任何标题行
        self._section_message = SystemMessage(
            content="""你是资深学术写作专家，正在撰写高质量的调研报告章节。请严格遵循以下规范：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【格式规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **标题层级**
   - 严禁输出一级标题（#）或二级标题（##）
   - 不要重复章节名称，直接开始正文
   - 可使用三级小标题（### ）划分逻辑小节，每章 2-4 个为宜
   - 小标题要简洁有力，体现该小节核心内容

2. **段落结构**
   - 每个自然段 3-6 句话，控制在 150-250 字
   - 段首句点明主题，段中展开论述，段尾总结或过渡
   - 避免单句成段，避免超长段落（>300字）
   - 段落间用逻辑推进而非机械衔接词过渡

3. **视觉元素**
   - **加粗**：仅用于首次出现的核心概念、关键术语（每段不超过 2-3 个）
   - *斜体*：可用于强调、外文术语、变量名
   - 表格：用于方法对比、性能指标、框架特性等结构化信息
   - 列表：用于并列要点、步骤说明、分类罗列（每项 1-2 句话）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【内容质量】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **学术严谨性**
   - 所有论断必须有文献支撑，使用 [编号] 标注引用
   - 引用需多样化，避免单一论文过度引用
   - 给出具体数值、实验设置、对比结果（如"准确率提升 15%"，而非"显著提升"）
   - 区分事实陈述与推测性观点

2. **技术深度**
   - 核心算法需说明原理、公式、复杂度
   - 框架/工具需说明版本、关键特性、适用场景
   - 实验需说明数据集、评估指标、基线方法
   - 对比分析需多维度（性能、效率、可扩展性等）

3. **逻辑连贯性**
   - 从问题→方法→实验→结论，逻辑链条完整
   - 前后概念一致，术语统一（如不混用 "代理" 与 "智能体"）
   - 新概念首次出现需简要解释
   - 适时承上启下，但避免"首先、其次、总之"等模板化表达

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【语言风格】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **推荐表达**：
- "研究表明..." / "实验证明..." / "分析发现..."
- "在此基础上..." / "基于上述分析..." / "该方法进一步..."
- "以 XX 为例..." / "如 XX 所示..." / "对比 XX 与 YY..."
- "从 XX 角度看..." / "就 XX 而言..." / "考虑到 XX..."

❌ **禁用表达**（AI 机械风格）：
- "首先、其次、最后" / "总而言之、综上所述"
- "值得注意的是" / "需要指出的是" / "不难发现"
- "显而易见" / "毋庸置疑" / "众所周知"
- "换言之" / "换句话说" / "具体而言"（除非真的在改述）

✅ **推荐过渡方式**：
- 因果："由于 XX，导致..." / "XX 的原因在于..."
- 递进："XX 不仅...，还..." / "在 XX 基础上，YY 进一步..."
- 转折："然而 XX 仍存在..." / "尽管 XX，但..."
- 并列："XX 与 YY 分别..." / "XX 和 YY 各自..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【特殊要求】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **表格示例**（方法对比）：
```
| 方法 | 核心思想 | 优势 | 局限 | 代表工作 |
|------|---------|------|------|---------|
| XX   | ...     | ...  | ...  | [1][2]  |
```

2. **代码/公式**：
   - 关键算法可用代码块（```python）或伪代码
   - 重要公式用 LaTeX 行内 `$...$` 或块级 `$$...$$`

3. **图表引用**：
   - 如需引用图表，使用"如图 1 所示"，但本次生成不包含实际图片

4. **术语规范**：
   - 中英文混排时，英文前后加空格（如"使用 Transformer 架构"）
   - 首次出现的英文术语标注中文（如"大型语言模型（Large Language Models, LLMs）"）
   - 后续使用可只用中文或只用缩写

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请直接开始撰写章节正文，体现专业性、可读性与学术价值的统一。
"""
        )
    
    @message_handler
    async def handle_batch(self, message: GradeBatchData, ctx: MessageContext) -> None:
        """接收汇总评级后一次性生成报告"""
        self._topic = message.topic
        self._approved_papers = [g for g in message.grades if g.approved]
        logger.info(f"收到汇总评级，共 {len(message.grades)} 篇，其中通过 {len(self._approved_papers)} 篇")
        
        if len(self._approved_papers) < settings.min_papers_for_report:
            logger.warning(
                f"通过数量低于阈值({settings.min_papers_for_report})，仍将生成报告"
            )
        
        if settings.writer_use_section_flow:
            await self._generate_by_sections(ctx)
        else:
            await self._generate_report(ctx)

    async def _generate_by_sections(self, ctx: MessageContext) -> None:
        """按章节循环撰写并将每章入库，最后合并生成报告"""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "-" + uuid.uuid4().hex[:6]
        sections = list(settings.section_outline)
        section_texts: List[str] = []

        for idx, section in enumerate(sections):
            section_content = await self._generate_single_section(section, run_id, idx, ctx)
            section_texts.append(f"## {section}\n\n{section_content}\n")
            
            # 入库当前章节
            try:
                emb = self._embedding.encode_single(section_content)
                self._chroma.upsert_if_changed(
                    ids=[f"section-{run_id}-{idx}"],
                    embeddings=[emb],
                    documents=[section_content],
                    metadatas=[{"type": "section", "run_id": run_id, "section": section}]
                )
            except Exception as e:
                logger.warning(f"章节入库失败: {section} - {e}")

        # 发布装配请求，由 AssemblerAgent 统一合并与引用去重
        await self.publish_message(
            AssembleRequest(topic=self._topic, run_id=run_id, sections=sections),
            topic_id=TopicId("AssemblerAgent", source=self.id.key)
        )
        logger.success("分章草稿已提交装配")

    async def _generate_single_section(self, section: str, run_id: str, idx: int, ctx: MessageContext) -> str:
        """生成单个章节内容，检索前文章节与知识库"""
        # 构造检索查询
        # 先做“章节前置规划”：从前文节选与论文分析中，提取关键词与所需文献类型
        plan = await self._plan_section_sources(section, ctx)
        keywords = ", ".join(plan.get("keywords", [])) if isinstance(plan, dict) else ""
        query_text = f"{self._topic} {section} {keywords}".strip()
        query_embedding = self._embedding.encode_single(query_text)

        # 检索前文章节（同一次run）
        prev_docs = self._chroma.retrieve_similar(query_embedding, n_results=settings.section_rag_top_k, where={"run_id": run_id})

        # 检索知识库摘要与分析
        kb_sum = self._chroma.retrieve_similar(query_embedding, n_results=settings.section_rag_top_k, where={"type": "summary"})
        kb_ana = self._chroma.retrieve_similar(query_embedding, n_results=settings.section_rag_top_k, where={"type": "analysis"})

        def _concat_docs(res: dict) -> str:
            docs = res.get("documents", [[]])
            lines = []
            for i, d in enumerate(docs[0][: settings.section_rag_top_k] if docs and docs[0] else []):
                lines.append(f"- 片段{i+1}: {d[:300]}...")
            return "\n".join(lines)

        context_prev = _concat_docs(prev_docs)
        context_sum = _concat_docs(kb_sum)
        context_ana = _concat_docs(kb_ana)

        # 构建提示词
        papers_summary = "\n\n".join([
            f"论文{i+1}: {p.title}\n分析：{p.analysis[:300]}..." for i, p in enumerate(self._approved_papers[: settings.section_rag_top_k])
        ])

        prompt = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【写作任务】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**研究主题**：{self._topic}
**当前章节**：{section}
**字数要求**：≥ {settings.section_min_words} 字（中文）
**深度等级**：{settings.section_detail_level}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【参考资料】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. 前文章节摘要**
{context_prev if context_prev else '（本章为首章，无前文参考）'}

**2. 知识库-论文摘要**
{context_sum if context_sum.strip() else '（暂无相关摘要）'}

**3. 知识库-深度分析**
{context_ana if context_ana.strip() else '（暂无相关分析）'}

**4. 核心论文详细分析**
{papers_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【撰写指南】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**内容组织**：
1. 可使用 2-4 个三级小标题（### ）划分逻辑小节
2. 每个小节包含 2-4 个自然段
3. 适当使用表格对比方法/框架/性能
4. 用列表罗列要点（如挑战、特性、方向）

**引用规范**：
- 所有论点必须引用上述论文，使用 [编号] 标注
- 引用要分散，避免单篇论文过度引用
- 给出具体数据（如"准确率 85%"、"延迟降低 40%"）

**语言要求**：
- 学术规范但不失可读性
- 避免"首先、其次、总之"等机械过渡
- 用因果、递进、转折等自然逻辑连接段落
- 术语统一，首次出现需中英文标注

**技术深度**：
- 算法需说明原理、公式（可用 LaTeX）、复杂度
- 框架需说明版本、特性、适用场景
- 实验需说明数据集、指标、基线
- 如需查询技术细节，可调用 MCP 工具

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请直接开始撰写"{section}"章节的正文内容（不要输出章节标题）：
"""

        # ReAct 工具循环：如启用 MCP，则允许模型发起工具调用
        messages = [self._section_message, UserMessage(content=prompt, source=self.id.key)]
        content: str = ""
        if settings.writer_use_mcp_tools:
            logger.info(f" MCP工具模式已启用，开始加载 MCP 服务器...")
            try:
                # 导入 MCP 工具 API
                from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
                
                server_defs = self._load_mcp_servers()
                logger.info(f"从配置读取 {len(server_defs)} 个 MCP 服务器定义")

                # 逐个服务器加载工具并合并
                tools = []
                import os as _os
                for sd in server_defs:
                    # 解析环境变量占位符
                    env_dict = sd.get("env", {}) or {}
                    resolved_env = {}
                    for k, v in env_dict.items():
                        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                            resolved_env[k] = _os.getenv(v[2:-1], "")
                        else:
                            resolved_env[k] = v
                    
                    # 创建服务器参数
                    params = StdioServerParams(
                        command=sd.get("command", "npx"),
                        args=sd.get("args", []),
                        env=resolved_env if resolved_env else None
                    )
                    
                    # 加载该服务器的工具
                    logger.info(f" 正在加载 MCP 服务器: {sd.get('name', 'unknown')} (command={params.command})")
                    server_tools = await mcp_server_tools(params)
                    tools.extend(server_tools)
                    logger.success(f" ✓ {sd.get('name', 'unknown')} 加载完成，工具数: {len(server_tools)}")
                
                logger.success(f"MCP 工具加载完成，总工具数：{len(tools)}")
                
                # 使用 tools 进行 ReAct 循环
                create_result = await self._model_client.create(
                    messages=messages,
                    tools=tools,
                    cancellation_token=ctx.cancellation_token,
                )
                
                def _is_func_call_list(obj) -> bool:
                    if not isinstance(obj, list):
                        return False
                    if not obj:
                        return False
                    # Duck-typing: each has name/arguments/id
                    return all(hasattr(c, "name") and hasattr(c, "arguments") and hasattr(c, "id") for c in obj)

                # ReAct 循环：处理工具调用
                max_turns = 10  # 最多10轮工具调用
                turn = 0
                while _is_func_call_list(create_result.content) and turn < max_turns:
                    turn += 1
                    # 记录函数调用
                    messages.append(AssistantMessage(content=create_result.content, source="assistant"))
                    logger.info(f" 模型发起 {len(create_result.content)} 个工具调用 (轮次 {turn}/{max_turns})")
                    results = []
                    for call in create_result.content:  # type: ignore
                        logger.info(f" 调用工具: {call.name} | 参数: {call.arguments[:100]}...")
                        try:
                            args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
                        except Exception:
                            args = {}
                        
                        # 找到对应的工具并执行
                        tool_result = None
                        for tool in tools:
                            if tool.name == call.name:
                                try:
                                    # 直接调用工具的 run_json 方法
                                    tool_result = await tool.run_json(args, ctx.cancellation_token)
                                    logger.success(f" {call.name} 执行成功")
                                    break
                                except Exception as e:
                                    logger.error(f" {call.name} 执行失败: {e}")
                                    tool_result = str(e)
                                    break
                        
                        if tool_result is None:
                            tool_result = f"工具 {call.name} 未找到"
                            logger.warning(f" {call.name} 未找到")
                        
                        results.append(
                            FunctionExecutionResult(
                                call_id=call.id,
                                content=str(tool_result),
                                is_error=isinstance(tool_result, str) and "失败" in tool_result,
                                name=call.name,
                            )
                        )
                    
                    messages.append(FunctionExecutionResultMessage(content=results))
                    create_result = await self._model_client.create(
                        messages=messages,
                        tools=tools,
                        cancellation_token=ctx.cancellation_token,
                    )
                
                # 终止于文本
                if isinstance(create_result.content, str):
                    content = self._remove_think_tags(create_result.content)
                else:
                    content = ""
                    
            except Exception as e:
                # 失败则退化为无工具一次生成
                logger.warning(f"MCP 工具模式失败，退化为普通生成: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                result = await self._model_client.create(
                    messages=messages,
                    cancellation_token=ctx.cancellation_token,
                )
                content = self._remove_think_tags(result.content) if isinstance(result.content, str) else ""
        else:
            result = await self._model_client.create(
                messages=messages,
                cancellation_token=ctx.cancellation_token,
            )
            content = self._remove_think_tags(result.content) if isinstance(result.content, str) else ""

        # 自审修订：核验事实一致性与术语统一（不引入新知识，仅基于上述上下文）
        revise_prompt = (
            "你是技术审校专家。请对下述章节进行快速核验与微调：\n"
            "- 统一术语；- 删除与前文重复的句子；- 发现可能的事实不一致时，提出更稳妥的表述；\n"
            "- 不要添加新的引用或虚构事实；- 保持段落结构与中文风格。\n\n"
            f"[章节草稿]\n{content}\n"
        )
        revise = await self._model_client.create(
            messages=[SystemMessage(content="你是严谨的技术编辑。"), UserMessage(content=revise_prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        content = self._remove_think_tags(revise.content) if isinstance(revise.content, str) else content

        # 生成简单引用列表：使用已批准论文标题作为引用键（后续可替换为更规范的元数据）
        citations = [p.title for p in self._approved_papers[: settings.section_rag_top_k]]

        # 发布当前章节草稿给 AssemblerAgent
        await self.publish_message(
            SectionDraft(
                topic=self._topic,
                run_id=run_id,
                section_id=str(idx),
                content=content,
                citations=citations,
            ),
            topic_id=TopicId("AssemblerAgent", source=self.id.key),
        )

        return content

    async def _plan_section_sources(self, section: str, ctx: MessageContext) -> dict:
        """前置规划：基于前文节选与论文分析，提取关键词/需要的文献类型（JSON）"""
        plan_prompt = (
            "请根据已完成的章节节选与论文分析，给出本章节所需的核心主题关键词与文献类型，"
            "仅输出JSON对象，键：keywords(list[str])、doc_types(list[str])。"
        )
        try:
            res = await self._model_client.create(
                messages=[SystemMessage(content="仅输出JSON，不要额外文字。"), UserMessage(content=plan_prompt, source=self.id.key)],
                cancellation_token=ctx.cancellation_token,
            )
            return json.loads(res.content) if isinstance(res.content, str) else {}
        except Exception:
            return {}

    def _remove_think_tags(self, text: str) -> str:
        """移除 <think>...</think> 标签及其内部内容（用于推理模型）"""
        import re
        # 移除 <think>...</think> 块（支持多行、嵌套）
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _load_mcp_servers(self) -> List[dict]:
        """从配置文件加载MCP服务器定义（返回原始字典列表）。"""
        if not settings.writer_use_mcp_tools:
            return []
        try:
            with open(settings.autogen_mcp_config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
            return list(conf.get("servers", []))
        except Exception:
            return []
    
    async def _generate_report(self, ctx: MessageContext):
        """生成报告"""
        logger.info(f"生成报告，共 {len(self._approved_papers)} 篇论文")
        
        # 构建提示词
        papers_summary = "\n\n".join([
            f"论文{i+1}: {p.title}\n分析：{p.analysis[:300]}..."
            for i, p in enumerate(self._approved_papers)
        ])
        
        prompt = f"研究主题：{self._topic}\n\n论文分析：\n{papers_summary}\n\n请生成调研报告。"
        
        # 生成报告
        result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=prompt, source=self.id.key)
            ],
            cancellation_token=ctx.cancellation_token
        )
        
        # 提取参考文献
        references = [f"[{i+1}] {p.title}" for i, p in enumerate(self._approved_papers)]
        
        # 发布到调度Agent
        await self.publish_message(
            ReportData(
                topic=self._topic,
                content=result.content,
                references=references
            ),
            topic_id=TopicId("CoordinatorAgent", source=self.id.key)
        )
        
        logger.success("报告生成完成")

