"""
LLM 模块 - 基于 LangChain ChatOpenAI 封装 DeepSeek API
支持 Thinking Mode 配置（V4 Pro / V4 Flash）

关键: reasoning_effort 是必传合法值（langchain-openai 源码无条件发送此字段）；
      extra_body 仅在 thinking=enabled 时传入，disabled 时不传避免冲突。
"""
from langchain_openai import ChatOpenAI

from .config import Settings


def create_llm(settings: Settings) -> ChatOpenAI:
    """创建 LLM 实例"""
    thinking_type = settings.deepseek_thinking              # "enabled" | "disabled"
    reasoning_effort = settings.deepseek_reasoning_effort or "low"

    # 构建 ChatOpenAI 参数
    llm_kwargs = {
        "model": settings.llm_model,
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
        "temperature": 0.3,
        "max_tokens": 2048,
        "streaming": True,
        "reasoning_effort": reasoning_effort,
    }

    # thinking=enabled 时通过 extra_body 开启思考模式
    # disabled 时不传 extra_body（V4 Flash 默认无思考，V4 Pro 默认有思考但 reasoning_effort 足以控制）
    if thinking_type == "enabled":
        llm_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    return ChatOpenAI(**llm_kwargs)
