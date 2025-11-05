# 快速开始指南

## 5 分钟上手

### 步骤 1：安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤 2：配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# 最小配置（必填）
API_KEY=your_api_key_here
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
MODEL_NAME=glm-4-flash
```

### 步骤 3：运行系统

```bash
python main.py
# 输入主题，例如：transformer
```

### 步骤 4：查看报告

生成的报告位于：`./cache/reports/YYYYMMDD_HHMMSS_主题.md`

---

## 常用配置

### 调整论文数量

```bash
# .env
MAX_PAPERS=20  # 减少采集数量，加快速度
```

### 启用分章写作

```bash
# .env
WRITER_USE_SECTION_FLOW=true
SECTION_MIN_WORDS=2000  # 每章最少 2000 字
```

### 启用 MCP 工具（高级）

1. 安装 Node.js（用于 MCP 服务器）
2. 配置 `.env`：
   ```bash
   WRITER_USE_MCP_TOOLS=true
   TAVILY_API_KEY=your_tavily_key
   ```
3. 配置 `autogenmcp.json`（参考 `autogenmcp.json.example`）

---

## 常见问题

### 问题 1：模型下载慢

**解决方案**：使用 HuggingFace 镜像

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 问题 2：API 调用失败

**排查步骤**：
1. 检查 `.env` 中的 `API_KEY` 是否正确
2. 检查 `BASE_URL` 是否匹配模型提供商
3. 确认 API 余额充足
4. 查看 `./logs/` 中的错误日志

### 问题 3：生成报告为空

**可能原因**：
- 论文搜索无结果（尝试更换关键词）
- 所有论文被评级拒绝（降低 `RISK_THRESHOLD`）
- API 调用失败（查看日志）

---

## 下一步

- 阅读 [完整文档](../README.md)
- 自定义章节目录（修改 `config/settings.py`）
- 集成自己的 LLM 模型
- 添加自定义智能体

