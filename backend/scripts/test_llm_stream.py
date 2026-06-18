"""测试 LangChain LLM.stream() 是否逐 token 产出"""
import time, sys
from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
llm = create_llm(settings)

messages = [
    {"role": "system", "content": "你是医疗助手"},
    {"role": "user", "content": "用三句话介绍感冒的治疗方法"},
]

print("Testing LLM.stream()...")
count = 0
start = time.time()
for chunk in llm.stream(messages):
    count += 1
    token = chunk.content if hasattr(chunk, "content") else str(chunk)
    t = time.time() - start
    if count <= 5 or count % 20 == 0:
        print(f"  [{t:.3f}s] chunk#{count}: {repr(token[:40])}")
print(f"Total: {count} chunks in {time.time()-start:.2f}s")
