"""检查 DeepSeek stream chunk 的完整结构"""
from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
llm = create_llm(settings)
messages = [{"role": "user", "content": "感冒了怎么办？一句话回答"}]

for i, chunk in enumerate(llm.stream(messages)):
    content = getattr(chunk, "content", "")
    reasoning = None
    if hasattr(chunk, "additional_kwargs"):
        reasoning = chunk.additional_kwargs.get("reasoning_content")
    if hasattr(chunk, "response_metadata"):
        reasoning = reasoning or chunk.response_metadata.get("reasoning_content")

    # Check all attributes for reasoning
    if i < 3 or content or i % 30 == 0:
        extra = {}
        if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
            extra = {k: str(v)[:80] for k, v in chunk.additional_kwargs.items()}
        print(f"  [{i}] content={repr(content[:30] if content else '')} | extra={extra} | type={type(chunk).__name__}")
        if i >= 3 and content:
            print(f"  ... (content started at chunk {i})")
            break
