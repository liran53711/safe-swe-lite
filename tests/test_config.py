import pytest
import yaml
from pydantic import ValidationError

from safe_swe_lite.config.loader import Config, load_config


def test_load_default_config():
    config = load_config()
    assert isinstance(config, Config)
    assert config.max_turns == 50
    assert config.command_timeout == 30
    assert config.model.provider == "mock"


def test_load_custom_yaml(tmp_path):
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(yaml.safe_dump({
        "workspace": "./examples/sample_project",
        "max_turns": 7,
        "model": {"provider": "mock", "mock_outputs": []},
        "guardrails": {"require_approval": ["git push"]},
        "feedback": {"validators": ["compile", "test"], "max_retries": 2},
        "memory": {"recent_window": 5},
    }))
    config = load_config(yaml_path)
    assert config.max_turns == 7
    assert config.feedback.max_retries == 2
    assert config.memory.recent_window == 5


def test_invalid_config_rejected(tmp_path):
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("max_turns: not-a-number\n")
    with pytest.raises(ValidationError):
        load_config(yaml_path)


def test_top_level_list_yaml_rejected(tmp_path):
    yaml_path = tmp_path / "list.yaml"
    yaml_path.write_text("- a\n- b\n")
    with pytest.raises(ValidationError):
        load_config(yaml_path)


def test_missing_file_falls_back_to_default():
    # 显式路径不存在时抛 FileNotFoundError（见 test_explicit_missing_path_raises）；
    # 无参调用在默认文件缺失时回退内置默认值
    config = load_config()
    assert isinstance(config, Config)


def test_unknown_config_key_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("max_turn: 100\n")  # 拼错键（少 s）
    with pytest.raises(ValidationError):
        load_config(p)


def test_explicit_missing_path_raises():
    try:
        load_config("definitely-missing.yaml")
        assert False, "should raise"
    except FileNotFoundError:
        pass


def test_default_yaml_inside_package():
    # 包内 default.yaml 可被资源加载器解析（钉打包路径）
    from importlib import resources
    raw = resources.files("safe_swe_lite.config").joinpath("default.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert data["max_turns"] == 50
