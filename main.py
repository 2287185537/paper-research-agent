"""主程序入口"""
import asyncio
from pathlib import Path
from workflows.sequential_workflow import ResearchWorkflow
from utils.logger import setup_logger
from loguru import logger


def init_directories():
    """初始化目录"""
    dirs = [
        "./cache/chroma",
        "./cache/models",
        "./cache/papers",
        "./cache/reports",
        "./logs"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


async def main():
    """主函数"""
    # 初始化日志
    setup_logger()
    
    # 初始化目录
    init_directories()
    
    # 欢迎信息
    print("\n" + "="*60)
    print("  基于 AutoGen 多智能体论文调研报告生成系统")
    print("="*60 + "\n")
    
    # 输入研究主题
    topic = input("请输入研究主题 (例如: machine learning, transformer): ").strip()
    
    if not topic:
        logger.error("主题不能为空")
        return
    
    logger.info(f"开始调研: {topic}")
    
    try:
        # 创建工作流
        workflow = ResearchWorkflow()
        
        # 执行工作流
        await workflow.run(topic)
        
    except KeyboardInterrupt:
        logger.warning("用户中断")
    except Exception as e:
        logger.exception(f"执行失败: {e}")
    
    print("\n程序结束\n")


if __name__ == "__main__":
    asyncio.run(main())

