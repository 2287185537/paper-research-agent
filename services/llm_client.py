"""LLM客户端封装"""
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from loguru import logger


class LLMClient:
    """智谱AI客户端（OpenAI SDK兼容）"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=2
        )
        logger.info(f"LLM客户端初始化: {model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """聊天接口（带重试）"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM响应: {len(content)}字符")
            return content
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ):
        """流式聊天接口"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"流式调用失败: {e}")
            raise
    
    def close(self):
        """关闭客户端"""
        self.client.close()
        logger.info("LLM客户端已关闭")

