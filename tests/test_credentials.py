"""Credential safety tests for the real LLM provider. All offline — no real API calls."""

from safe_swe_lite.llm.litellm_provider import (
    ApiKeyNotFound,
    get_api_key,
    mask_key,
    resolve_api_key,
)


def test_mask_key_hides_secret():
    # spec: 长 key 首 6 尾 4（key[:6] + "..." + key[-4:]）
    assert mask_key("sk-abc123def456") == "sk-abc...f456"


def test_resolve_api_key_env_var(monkeypatch):
    monkeypatch.setenv("SAFE_SWE_LITE_API_KEY", "sk-test")
    assert resolve_api_key() == "sk-test"


def test_resolve_api_key_raises_when_missing(monkeypatch):
    for var in ("SAFE_SWE_LITE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    import safe_swe_lite.llm.litellm_provider as lp
    monkeypatch.setattr(lp.keyring, "get_password", lambda *a, **k: None)
    try:
        resolve_api_key()
        assert False, "should raise"
    except ApiKeyNotFound:
        pass


def test_get_api_key_prefers_keyring_over_env(monkeypatch):
    import safe_swe_lite.llm.litellm_provider as lp
    monkeypatch.setenv("SAFE_SWE_LITE_API_KEY", "sk-from-env")
    monkeypatch.setattr(lp.keyring, "get_password", lambda *a, **k: "sk-from-keyring")
    assert get_api_key() == "sk-from-keyring"


def test_get_api_key_falls_back_when_keyring_unavailable(monkeypatch):
    import safe_swe_lite.llm.litellm_provider as lp
    monkeypatch.setenv("SAFE_SWE_LITE_API_KEY", "sk-from-env")
    monkeypatch.setattr(lp.keyring, "get_password", lambda *a, **k: (_ for _ in ()).throw(KeyError("no backend")))
    assert get_api_key() == "sk-from-env"


def test_mask_key_boundaries():
    assert mask_key("1234567890") == "**********"  # 恰 10 全掩码
    assert mask_key("12345678901") == "123456...8901"  # 11 起首 6 尾 4
    assert mask_key("") == ""
