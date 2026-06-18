"""绕过 Flask，直接测试 LLM 实例配置和调用"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
print(f"Config: model={settings.llm_model}")
print(f"  thinking={settings.deepseek_thinking}")
print(f"  reasoning_effort={settings.deepseek_reasoning_effort}")

llm = create_llm(settings)
print(f"\nLLM instance:")
print(f"  model_name={llm.model_name}")
print(f"  reasoning_effort={llm.reasoning_effort}")
print(f"  extra_body={llm.extra_body}")
print(f"  streaming={llm.streaming}")

# 试着调用
print(f"\nCalling LLM.stream() with test message...")
try:
    msg = [{"role": "user", "content": "说一个字：好"}]
    for i, chunk in enumerate(llm.stream(msg)):
        content = chunk.content
        if content and content.strip():
            print(f"  [{i}] content: {content.strip()}")
            break
        if i > 10:
            print(f"  [{i}] empty content")
            break
    print("SUCCESS!")
except Exception as e:
    print(f"FAILED: {e}")
