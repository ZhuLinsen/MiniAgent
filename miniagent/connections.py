"""CLI connection profiles; secrets stay in the environment, OS vault or memory."""
import asyncio
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from any_llm import AnyLLM
from rich.prompt import Prompt
from rich.text import Text

from .llm import close_client, provider_client

PROVIDERS = {"deepseek": "DeepSeek", "dashscope": "Qwen / DashScope", "zai": "GLM / Z.ai",
             "moonshot": "Kimi / Moonshot", "minimax": "MiniMax", "openai": "OpenAI",
             "anthropic": "Anthropic Claude", "gemini": "Google Gemini"}
_secrets = {}


def home():
    return Path(os.environ.get("MINIAGENT_HOME", str(Path.home() / ".miniagent"))).expanduser()


def read_profiles():
    path = home() / "connections.json"
    if not path.exists():
        return {"model": "", "models": {}, "providers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _validate(data)
        return data
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Invalid connections.json; fix or restore it before configuring models") from error


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", value):
        raise ValueError("Provider name must be a lowercase identifier")
    return value


def _model(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError("A nonempty model ID is required")
    return value.strip()


def _base(value):
    if not isinstance(value, str) or any(ord(c) <= 32 for c in value):
        raise ValueError("Invalid base URL")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Use an HTTP(S) base URL without embedded credentials, query or fragment")
    return value.rstrip("/")


def _validate(data):
    if set(data) != {"model", "models", "providers"} or not isinstance(data["model"], str):
        raise ValueError("Invalid profile fields")
    if data["model"]:
        provider, separator, model = data["model"].partition(":")
        if not separator:
            raise ValueError("Stored model requires provider:model-id")
        _identifier(provider)
        _model(model)
    for provider, models in data["models"].items():
        _identifier(provider)
        if not isinstance(models, list):
            raise ValueError("Invalid model list")
        for model in models:
            _model(model)
    for provider, entry in data["providers"].items():
        _identifier(provider)
        if set(entry) != {"type", "base_url", "api_key_env"} or entry["type"] != "openai-compatible":
            raise ValueError("Profiles store endpoint metadata, never API keys")
        _base(entry["base_url"])
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", entry["api_key_env"]):
            raise ValueError("Invalid credential environment variable")


def save_model(provider, model, entry=None):
    data = read_profiles()
    data["model"] = f"{_identifier(provider)}:{_model(model)}"
    data["models"][provider] = list(dict.fromkeys([model, *data["models"].get(provider, [])]))
    if entry:
        data["providers"][provider] = entry
    _validate(data)
    path = home() / "connections.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _vault():
    import keyring
    backend = keyring.get_keyring()
    candidates = getattr(backend, "backends", [backend])
    for candidate in candidates:
        if type(candidate).__module__ in {"keyring.backends.Windows", "keyring.backends.macOS",
                "keyring.backends.SecretService", "keyring.backends.kwallet", "keyring.backends.libsecret"}:
            return candidate
    raise RuntimeError("No supported OS credential store")


def credential(env, *, persisted=False):
    value = _secrets.get(env) or os.environ.get(env)
    if value or not persisted:
        return value
    try:
        return _vault().get_password("miniagent", env)
    except Exception:
        return None


def error_text(error, *keys):
    """Keep provider error bodies from echoing known process credentials."""
    text = str(error)
    values = [*keys, *_secrets.values(), *(v for k, v in os.environ.items() if k.endswith("_API_KEY"))]
    for value in sorted({v for v in values if v}, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    return f"{type(error).__name__}: {text}"


def store_credential(env, value):
    _secrets[env] = value
    try:
        _vault().set_password("miniagent", env, value)
        return True
    except Exception:
        return False


def choose(console, title, values):
    values = list(dict.fromkeys(values))
    for index, value in enumerate(values, 1):
        console.print(Text(f"{index:02d}  {value}"))
    answer = Prompt.ask(title, console=console).strip()
    if answer.isdigit() and 1 <= int(answer) <= len(values):
        return values[int(answer) - 1]
    return answer


async def discover(console, provider, *, providers, api_key=None, base_url=None):
    client = None
    try:
        client = provider_client(provider, providers=providers, api_key=api_key, base_url=base_url)
        models = await asyncio.wait_for(client.alist_models(), timeout=10)
        return sorted({_model(m.id) for m in models if not api_key or api_key not in m.id})[:200]
    except Exception as error:
        console.print(Text(f"Model listing unavailable ({type(error).__name__}); enter a model ID manually."))
        return []
    finally:
        if client:
            await close_client(client)


async def connect(console, cfg):
    profiles = read_profiles()
    names = [*PROVIDERS, "custom"]
    console.print(Text("Model provider: " + ", ".join(f"{p} ({label})" for p, label in PROVIDERS.items())))
    provider = _identifier(choose(console, "Provider number or name", names))
    entry = None
    if provider == "custom":
        provider = _identifier(Prompt.ask("Provider name", console=console).strip())
        if provider in PROVIDERS:
            raise ValueError("Use a distinct name for a custom endpoint")
        base = _base(Prompt.ask("OpenAI-compatible base URL", console=console).strip())
        env = "MINIAGENT_" + provider.encode().hex().upper() + "_API_KEY"
        entry = {"type": "openai-compatible", "base_url": base, "api_key_env": env}
    else:
        try:
            env = AnyLLM.get_provider_class(provider).ENV_API_KEY_NAME
        except ImportError as error:
            raise ValueError("Provider SDK is unavailable; install the matching any-llm extra or use a custom endpoint") from error
    key = credential(env, persisted=provider in profiles["models"])
    supplied = Prompt.ask(f"API key (hidden; empty keeps {env})", password=True, console=console).strip()
    key = supplied or key
    if not key:
        raise ValueError(f"Missing credential: {env}")
    providers = dict(cfg.providers)
    if entry:
        providers[provider] = entry
    models = await discover(console, provider, providers=providers, api_key=key)
    model = _model(choose(console, "Model number or ID", models))
    if key in json.dumps({"provider": provider, "model": model, "entry": entry}):
        raise ValueError("Credential must not appear in connection metadata")
    save_model(provider, model, entry)
    if supplied:
        saved = store_credential(env, key)
        console.print(Text("Key saved in OS credential store." if saved else
            f"OS credential store unavailable; key is only in this process. Install miniagent[credentials] or export {env} before the next launch."))
    console.print(Text(f"Configured {provider}:{model}. Model listing is not a tool-call acceptance test."))
    return f"{provider}:{model}"


async def select_model(console, cfg):
    profiles = read_profiles()
    current = cfg.llm.model.partition(":")[0] if ":" in cfg.llm.model else "openai"
    names = list(dict.fromkeys([*profiles["models"], *cfg.providers, current]))
    provider = _identifier(choose(console, "Connected provider", names))
    if provider not in names:
        raise ValueError("Choose a configured provider or use /connect first")
    entry = cfg.providers.get(provider)
    env = entry.get("api_key_env") if entry else AnyLLM.get_provider_class(provider).ENV_API_KEY_NAME
    key = credential(env, persisted=provider in profiles["models"]) if env else None
    if provider == current:
        key = cfg.llm.api_key or key
    models = await discover(console, provider, providers=cfg.providers, api_key=key,
                            base_url=cfg.llm.api_base if provider == current else None)
    models = list(dict.fromkeys([*models, *profiles["models"].get(provider, [])]))
    model = _model(choose(console, "Model number or ID", models))
    save_model(provider, model)
    return f"{provider}:{model}"
