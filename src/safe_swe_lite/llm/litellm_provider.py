"""Real LLM provider via litellm + keyring credential storage."""

import getpass
import os

import keyring

SERVICE_NAME = "safe-swe-lite"
ENV_KEY_NAMES = ("SAFE_SWE_LITE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")


class ApiKeyNotFound(Exception):
    pass


def mask_key(key: str) -> str:
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def get_api_key() -> str:
    """Keyring first, environment fallback. Never returns masked value.

    keyring 在无 Secret Service daemon 的环境（headless Linux/Render 容器）
    会抛 KeyringError——此时降级到环境变量而非崩溃。
    """
    from dotenv import load_dotenv

    load_dotenv()  # 显式加载 .env（不依赖 litellm 的 import 副作用）
    try:
        stored = keyring.get_password(SERVICE_NAME, "api_key")
    except Exception:  # noqa: BLE001 - keyring 后端不可用时降级 env
        stored = None
    if stored:
        return stored
    for name in ENV_KEY_NAMES:
        value = os.getenv(name)
        if value:
            return value
    raise ApiKeyNotFound(
        "no API key found. Run 'safe-swe-lite auth' or set SAFE_SWE_LITE_API_KEY"
    )


def resolve_api_key() -> str:
    return get_api_key()


def auth_command() -> None:
    print("Enter your API key (input is hidden):")
    key = getpass.getpass("API key: ").strip()
    if not key:
        print("aborted: empty key")
        return
    try:
        keyring.set_password(SERVICE_NAME, "api_key", key)
    except Exception:  # noqa: BLE001 - keyring 不可用（headless Linux）时提示改用 env
        print("keyring unavailable on this system; use the SAFE_SWE_LITE_API_KEY environment variable instead")
        return
    print(f"saved. status: configured (masked: {mask_key(key)})")


class LiteLLMProvider:
    """Real LLM via litellm text completion.

    与 MockLLM 同一接口：query(messages) 返回 {"message": "<json string>"}。
    LLM 被要求只输出 JSON action（见 SYSTEM_PROMPT），parse_action 负责解析。
    """

    SYSTEM_PROMPT = (
        "You are a coding agent. Respond ONLY with a single JSON object of the form "
        '{"action": "<tool_name>", "parameters": {...}}. '
        "Available actions: read_file, write_file, edit_file, run_command, "
        "search_pattern, list_files, submit."
    )

    def __init__(self, model_name: str | None = None):
        import litellm

        self.litellm = litellm
        self.model_name = model_name or os.getenv(
            "SAFE_SWE_LITE_MODEL", "anthropic/claude-sonnet-4-5"
        )

    def query(self, messages: list[dict], **kwargs) -> dict:
        if messages and messages[0].get("role") == "system":
            full = list(messages)
        else:
            full = [{"role": "system", "content": self.SYSTEM_PROMPT}, *messages]
        response = self.litellm.completion(
            model=self.model_name,
            messages=full,
            api_key=get_api_key(),
            **kwargs,
        )
        return {"message": response.choices[0].message.content}
