# Interactive model connections

The native CLI can configure a provider without editing `.env`. It reuses
the same any-llm client factory as normal execution; the adapter has no UI logic.

```bash
miniagent --connect
miniagent
```

`--connect` saves setup and exits without starting a task. A normal first launch
opens the guide only when a model/credential is missing, stdin is a TTY and no
`--prompt` was supplied. Noninteractive automation never prompts for credentials
and returns 2 for missing configuration. `--legacy` retains explicit setup.
EOF or Ctrl+C cancels initial setup. Keep provider API keys out of CLI arguments.

## Provider and model selection

The menu covers DeepSeek, DashScope/Qwen, Z.ai/GLM, Moonshot/Kimi, MiniMax,
OpenAI, Anthropic and Gemini, plus a custom OpenAI-compatible endpoint.
Provider IDs and credential variable names come from the installed SDK. If
a native provider's optional SDK is missing, install that provider's any-llm
extra or configure an explicitly supplied compatible endpoint.
This menu is not a claim that every provider has passed live acceptance.

Keys are entered with hidden input. A blank key keeps the existing credential.
Model discovery uses the SDK's `alist_models()`, bounded to 10 seconds and 200
displayed IDs; the temporary client is closed. Unavailable/unsupported discovery
falls back to manual model ID entry. A successful listing is not proof of
model-specific tool/stream compatibility; the first task may still be rejected.

REPL commands:

| Command | Behavior |
| --- | --- |
| `/connect` | Add/reconfigure a provider and select its model. |
| `/models` | Choose a configured provider, then a listed, remembered or manual ID. |
| `/model` | Show the current model. |
| `/model provider:model-id` | Switch the current runtime without changing the saved default. |

These guided commands require a TTY. Switching constructs the new client before
unloading the old one and then starts a fresh session, preserving old session files.
Skill settings remain active. Constructor failure leaves the old connection usable.

For a custom endpoint supply a distinct lowercase provider identifier, HTTP(S)
base URL, hidden key and model ID. URLs with user-info, query strings or fragments
are rejected to avoid embedding credentials. Profile metadata stores its URL and
credential environment variable name; the name is derived uniquely from the
provider identifier. Afterwards `miniagent --model yourprovider:model-id` uses
the saved endpoint. A custom provider configured only in an explicit JSON file
still requires that file; `/models` remembers model IDs, not a copy of arbitrary JSON.

## Persistence and credentials

`MINIAGENT_HOME/connections.json` contains only `model`, remembered `models`,
and custom `providers` (`type`, `base_url`, `api_key_env`). It is replaced atomically.
Malformed profiles fail visibly without being overwritten. Concurrent configuration
is last-writer-wins; run one setup at a time. Keys are never written to this file.

Install optional OS credential support with:

```bash
python -m pip install 'miniagent[credentials]'
```

Supported stores are the built-in Windows vault, macOS Keychain, Secret Service,
KWallet and libsecret. Insecure third-party file backends are not used. If no
supported store is available or saving fails, a supplied key stays only in process
memory; the CLI says so. The next process must use an environment key or reconnect.
Do not confuse saving model metadata with persisting authentication.

Normal credential lookup prefers the environment over the OS vault. A key typed
in the current process is an explicit session override of the provider environment
key; after restart the environment wins again. Explicit `--api-key`, JSON `api_key`
or `LLM_API_KEY` still override provider-specific lookup. Prefer provider keys
instead of a global compatibility key when switching between native providers.

Model precedence is CLI > explicit JSON > environment > saved default.
Explicit JSON custom providers override same-named saved endpoints. `LLM_API_BASE`
and `--base-url` remain intentional compatibility overrides. Clear these overrides
when adopting a new saved default; guided setup does not rewrite your environment
or command-line options. Keyless custom endpoints in existing JSON remain supported.

## Verification and rollback

Offline tests cover hidden prompts, environment/JSON/CLI precedence, secure-vault
and memory fallback, rejected secret-bearing URLs, cancellation, corrupt profiles,
SDK HTTP model listing, TTY guards, session reset and old-client cleanup.
Windows WinVault roundtrip was exercised with an ephemeral test credential and
deleted afterwards. Other native OS stores require platform-specific manual checks;
CI uses isolated credential-store fixtures, not real account credentials.

Rollback this PR restores explicit configuration. Keep provider environment keys
and `--model` or JSON settings for the older CLI. Profile metadata is compatible
data, not a session format change; preserve sessions and OS-stored credentials.
