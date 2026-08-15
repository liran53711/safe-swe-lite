"""YAML config -> Pydantic Config with validation."""

from importlib import resources
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# 包内资源：editable 与 wheel 安装下都解析到包内 default.yaml，
# 不依赖源树相对路径（parents[3] 在 wheel 布局下会指错位置）
DEFAULT_CONFIG_RESOURCE = resources.files("safe_swe_lite.config").joinpath("default.yaml")


def _default_config_path() -> Path:
    return Path(str(DEFAULT_CONFIG_RESOURCE))


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "mock"
    mock_outputs: list[str] = Field(default_factory=list)
    model_name: str = ""


class GuardrailConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocklist: list[str] = Field(default_factory=list)
    standalone: list[str] = Field(default_factory=list)
    block_unless_regex: dict[str, str] = Field(default_factory=dict)
    require_approval: list[str] = Field(default_factory=list)
    banned_symbols: list[str] = Field(default_factory=list)


class FeedbackConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validators: list[str] = Field(default_factory=lambda: ["compile", "test"])
    max_retries: int = 3


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recent_window: int = 10
    embedding: bool = False


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace: str = "./examples/sample_project"
    max_turns: int = 50
    timeout_seconds: int = 600
    command_timeout: int = 30
    model: ModelConfig = ModelConfig()
    guardrails: GuardrailConfig = GuardrailConfig()
    feedback: FeedbackConfig = FeedbackConfig()
    memory: MemoryConfig = MemoryConfig()


def load_config(path: Path | str | None = None) -> Config:
    if path is None:
        path = _default_config_path()
        if not path.exists():
            return Config()
    else:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValidationError.from_exception_data(
            "Config",
            [{"loc": (), "msg": "top-level YAML must be a mapping", "type": "value_error",
              "input": data, "ctx": {"error": ValueError("top-level YAML must be a mapping")}}],
        )
    return Config(**data)
