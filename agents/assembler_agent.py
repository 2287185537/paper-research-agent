"""报告装配Agent"""
from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from utils.message_types import SectionDraft, AssembleRequest, ReportData
from loguru import logger
from typing import Dict, List, Optional
import re


@type_subscription(topic_type="AssemblerAgent")
class AssemblerAgent(RoutedAgent):
    """装配Agent - 收集各章节草稿并统一合并与去重引用"""

    def __init__(self, model_client: Optional[ChatCompletionClient] = None):
        super().__init__("装配Agent")
        # 以 run_id 作为一次装配会话的键
        self._drafts_by_run: Dict[str, Dict[str, SectionDraft]] = {}
        self._model_client = model_client

    @message_handler
    async def handle_section(self, message: SectionDraft, ctx: MessageContext) -> None:
        """收集单章草稿"""
        run_store = self._drafts_by_run.setdefault(message.run_id, {})
        run_store[message.section_id] = message
        logger.info(f"收集章节草稿: run={message.run_id}, section={message.section_id}")

    @message_handler
    async def handle_assemble(self, message: AssembleRequest, ctx: MessageContext) -> None:
        """根据给定章节顺序合并草稿，统一引用并发布最终报告"""
        run_store = self._drafts_by_run.get(message.run_id, {})

        ordered_sections: List[str] = message.sections
        parts: List[str] = []
        citations: List[str] = []

        for idx, sec in enumerate(ordered_sections):
            draft = run_store.get(str(idx)) or run_store.get(sec)
            if not draft:
                logger.warning(f"缺少章节草稿: index={idx}, name={sec}")
                continue
            parts.append(f"## {sec}\n\n{draft.content}\n")
            citations.extend(draft.citations)

        # 引用去重，保持出现顺序
        seen = set()
        dedup_citations: List[str] = []
        for c in citations:
            if c not in seen:
                seen.add(c)
                dedup_citations.append(c)

        draft_report = "\n".join(parts)

        # 后处理：清理技术审校痕迹、学术化润色、增加排版优化
        final_content = self._post_process_report(draft_report)
        
        # 若提供模型，做终稿润色
        if self._model_client:
            try:
                final_content = await self._polish_final_report(final_content, message.topic, ctx)
            except Exception as e:
                logger.warning(f"终稿润色失败，使用后处理版本: {e}")

        await self.publish_message(
            ReportData(topic=message.topic, content=f"# {message.topic}领域调研报告\n\n" + final_content, references=dedup_citations),
            topic_id=TopicId("CoordinatorAgent", source=self.id.key),
        )
        logger.success("装配完成，已发布最终报告")

    def _post_process_report(self, raw: str) -> str:
        """后处理报告：移除技术审校标记、AI衔接词、过度加粗、标准化格式"""
        # 1. 移除技术审校章节标记
        lines = raw.split("\n")
        out_lines: List[str] = []
        skip_block = False
        for line in lines:
            stripped = line.strip()
            # 跳过技术审校标记行
            if any(kw in stripped for kw in ["[章节修订稿]", "[章节核验后版本]", "技术审校结果", "修改后的章节", "主要修改说明", "修改要点", "主要调整"]):
                skip_block = True
                continue
            # 遇到下一个二级标题，恢复正常
            if line.startswith("##") and not any(kw in stripped for kw in ["修改", "审校"]):
                skip_block = False
            if not skip_block:
                out_lines.append(line)
        
        text = "\n".join(out_lines)
        
        # 2. 移除 AI 常用机械衔接词（段首）
        ai_transitions = [
            r"^首先[，。、：]",
            r"^其次[，。、：]", 
            r"^再者[，。、：]",
            r"^最后[，。、：]",
            r"^总而言之[，。、：]",
            r"^综上所述[，。、：]",
            r"^值得注意的是[，。、：]",
            r"^值得一提的是[，。、：]",
            r"^需要指出的是[，。、：]",
            r"^此外[，。、：]",
            r"^另外[，。、：]",
            r"^进一步地[，。、：]",
            r"^与此同时[，。、：]",
            r"^在此背景下[，。、：]",
            r"^基于上述分析[，。、：]",
            r"^具体而言[，。、：]",
            r"^换言之[，。、：]",
        ]
        for pattern in ai_transitions:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)
        
        # 3. 减少过度加粗：每个自然段保留不超过 3 个加粗
        paragraphs = text.split("\n\n")
        cleaned_paragraphs = []
        for para in paragraphs:
            # 统计加粗数量
            bold_matches = re.findall(r"\*\*(.+?)\*\*", para)
            if len(bold_matches) > 3:
                # 保留前 3 个，其余去掉加粗
                for i, match in enumerate(bold_matches):
                    if i >= 3:
                        para = para.replace(f"**{match}**", match, 1)
            cleaned_paragraphs.append(para)
        text = "\n\n".join(cleaned_paragraphs)
        
        # 4. 清理重复空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()

    async def _polish_final_report(self, content: str, topic: str, ctx: MessageContext) -> str:
        """终稿润色：学术化、自然化、排版优化"""
        if not self._model_client:
            return content
        
        prompt = f"""你是资深学术编审专家，正在对一份调研报告进行终稿润色。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【润色目标】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

将原始报告提升为**专业、流畅、可读性强**的高质量学术文档。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【核心任务】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **语言优化**
   - 消除 AI 机械风格（"首先、其次、总之、值得注意的是"等）
   - 改用自然的学术表达（因果、递进、转折）
   - 保持专业性的同时提升可读性
   - 术语统一（如统一使用"代理"或"智能体"）

2. **逻辑连贯**
   - 确保段落间逻辑流畅，论点→论据→结论链条完整
   - 章节间承上启下自然，避免突兀跳转
   - 相同概念在不同章节保持一致表述

3. **排版美化**
   - 适度增加三级小标题（### ）划分小节，每章 2-4 个
   - 小标题简洁有力，体现核心内容
   - 控制段落长度（150-250 字），避免超长段落
   - 加粗限制在核心概念（每段不超过 2-3 个）
   - 表格用于对比信息（方法、性能、框架特性）

4. **学术规范**
   - 保留所有引用标注 [编号]，不得删除或添加
   - 统一术语，首次出现给出中英文（如"大型语言模型（LLMs）"）
   - 数据表述具体（"提升 15%"，而非"显著提升"）
   - 区分事实陈述与推测观点

5. **细节完善**
   - 修正明显的语法错误、标点误用
   - 中英文混排时，英文前后加空格
   - 删除编辑痕迹（"技术审校"、"修订稿"等）
   - 清理重复内容与冗余表述

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【严格禁止】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 添加原文未提及的引用或虚构内容
❌ 重复输出章节标题
❌ 改变原文的核心观点与论据
❌ 删除或修改引用编号
❌ 使用过于口语化或夸张的表述

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【报告信息】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**主题**：{topic}

**原始报告**：
{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请直接输出润色后的 Markdown 报告正文，体现专业、流畅、准确的统一。"""

        try:
            result = await self._model_client.create(
                messages=[
                    SystemMessage(content="你是专业学术编审，仅输出润色后的Markdown报告正文。"),
                    UserMessage(content=prompt, source=self.id.key)
                ],
                cancellation_token=ctx.cancellation_token
            )
            final = result.content if isinstance(result.content, str) else content
            return self._remove_think_tags(final)
        except Exception:
            return content

    def _remove_think_tags(self, text: str) -> str:
        """移除 <think>...</think> 标签及其内部内容（用于 MiniMax-M2 等推理模型）"""
        import re
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()
