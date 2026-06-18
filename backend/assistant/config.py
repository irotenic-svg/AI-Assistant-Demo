"""
配置管理模块 - 加载 .env 环境变量
参考 AI-CRM 项目的 Settings 模式
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件（项目根目录）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)


@dataclass
class Settings:
    """应用配置"""
    # DeepSeek LLM
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"))

    # Thinking Mode: "enabled" | "disabled"（V4 Pro 默认 enabled，Flash 推荐 disabled）
    deepseek_thinking: str = field(default_factory=lambda: os.getenv("DEEPSEEK_THINKING", "disabled"))
    # Reasoning Effort: low | medium | high | max | xhigh（thinking=enabled 时生效）
    deepseek_reasoning_effort: str = field(default_factory=lambda: os.getenv("DEEPSEEK_REASONING_EFFORT", "low"))

    # Flask
    flask_env: str = field(default_factory=lambda: os.getenv("FLASK_ENV", "development"))
    flask_host: str = field(default_factory=lambda: os.getenv("FLASK_HOST", "0.0.0.0"))
    flask_port: int = field(default_factory=lambda: int(os.getenv("FLASK_PORT", "5000")))

    # Vector Store
    chroma_dir: str = field(default_factory=lambda: os.getenv("CHROMA_DIR", "./backend/data/chroma"))

    # Data
    processed_data_dir: str = field(default_factory=lambda: os.getenv("PROCESSED_DATA_DIR", "./backend/data/processed"))
    raw_data_dir: str = field(default_factory=lambda: os.getenv("RAW_DATA_DIR", "E:/ProgramData/DataSet"))

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "auto"  # "auto", "cuda", or "cpu"

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.45

    # Memory
    memory_window_size: int = 10

    @property
    def llm_api_key(self) -> str:
        return self.deepseek_api_key

    @property
    def llm_base_url(self) -> str:
        return self.deepseek_base_url

    @property
    def llm_model(self) -> str:
        return self.deepseek_model


# 全局配置实例
def load_settings() -> Settings:
    """加载并返回配置实例"""
    return Settings()
