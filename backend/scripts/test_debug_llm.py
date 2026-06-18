"""直接测 LLM 实例看 extra_body 实际值"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
print(f"model: {settings.llm_model}")
print(f"thinking: {settings.deepseek_thinking}")
print(f"reasoning_effort: {settings.deepseek_reasoning_effort}")

llm = create_llm(settings)

# 检查 ChatOpenAI 实例属性
print(f"\nChatOpenAI params:")
print(f"  model: {llm.model_name}")
print(f"  streaming: {llm.streaming}")
print(f"  temperature: {llm.temperature}")
print(f"  max_tokens: {llm.max_tokens}")

# 检查 extra_body
if hasattr(llm, 'extra_body'):
    print(f"  extra_body: {llm.extra_body}")
else:
    # Try to find it in model_kwargs or other attrs
    for attr in ['model_kwargs', '_default_params', 'kwargs', '_identifying_params']:
        if hasattr(llm, attr):
            val = getattr(llm, attr)
            if isinstance(val, dict) and ('extra_body' in val or 'reasoning_effort' in val):
                print(f"  {attr}: {val}")

# Try to find reasoning params
import inspect
for name in dir(llm):
    if 'reasoning' in name.lower() or 'extra' in name.lower() or 'thinking' in name.lower():
        val = getattr(llm, name, None)
        if not callable(val):
            print(f"  {name}: {val}")
