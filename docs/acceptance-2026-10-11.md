# 2026-10-11 acceptance evidence

Scope: v0.2.0a1, Windows, Python 3.12.10. These are measured results, not
a stable v0.3 or full original-plan acceptance claim.

## Real API and coding task

The user selected Anspire for low-cost verification. Endpoint:
`https://open-gateway.anspire.cn/v6`, using the OpenAI-compatible protocol.
This verifies the gateway path, not the DeepSeek/DashScope/Anthropic native endpoints.

| Requested model ID through Anspire | Ordinary reply | Multi-turn tool | Streamed tool |
| --- | --- | --- | --- |
| `qwen3.5-flash` | passed | passed | passed |
| `deepseek-v4-flash` | passed | passed | passed |

Each model passed the three existing live pytest cases. The tool must actually
run with `n=2`, produce `3`, and feed the result into a second model request;
the streamed case also requires text chunks. Separate seven-case observation
recorded all passes including the coding task.
Live-test SDK versions: any-llm-sdk 1.33.0 and OpenAI 2.44.0, matching the
project's locked development environment. The minimal wheel measurement below
uses a fresh dependency resolution, rather than the development lock.

The Qwen coding demo created a temporary `calc.py` with subtraction instead of
addition and a fixed test expecting `add(2, 3) == 5`. The model called
`read → edit → bash`; the test printed `TEST PASSED`. A separate process reran
the test and verified the test file was unchanged. This is a small real task,
not evidence for arbitrary repository-scale coding ability.

The acceptance code requests a 512-token completion cap for OpenAI-compatible
models, a 30-second request timeout, three steps for the add-one case and six
for the coding demo. Native providers request `max_tokens=256` instead.
One initial 256-token ordinary-response run ended incomplete; the runtime
correctly rejected it. The shorter prompt and reasoning-inclusive limit then
passed. Requested token limits depend on gateway/provider enforcement.

Secrets were passed only to child-process environments, never committed,
included in reports or printed. Reports contain model IDs, timings, tool names
and usage, without prompts, tool arguments, private paths or credentials.

Reproduce after configuring an explicit gateway key/base in the environment
or a JSON custom provider (do not pass secrets on the command line):

```bash
python -m pytest tests/test_llm.py -q -m live
python scripts/live_coding_smoke.py --model provider:model-id --report temp/coding-demo.json
```

For pytest also set `MINIAGENT_TEST_MODEL=provider:model-id`. The model is not
hardcoded in either verification entry point. CLI overrides and JSON use the
same credential resolution as normal execution.

Selected models appear in [Anspire's pricing table](https://maas.anspire.cn/pricing):
Qwen Flash input/output ¥0.2/¥2 and DeepSeek Flash ¥0.65/¥1.3 per million
tokens at the time checked. The account invoice is authoritative; no billed
total is claimed. See [official integration documentation](https://maas.anspire.cn/docs).

## Minimal installed wheel measurements

Built the wheel, installed it without MCP/legacy extras into a disposable venv,
and ran outside the source checkout using isolated Python (`-I`). Readonly file
access and denial of writes passed; `requests`, `psutil` and `mcp` were absent.

| Measurement | Windows local result |
| --- | ---: |
| Wheel | 69,643 bytes |
| Installed site-packages, including dependencies and bytecode | 33,763,904 bytes (32.2 MiB) |
| Cached uv installation | 0.8385 s |
| New-process `import miniagent`, median of 5 | 0.2058 s |
| New-process CLI `--help`, median of 5 | 0.2128 s |

These timings include Python process startup and warm OS/dependency caches.
They exclude the base interpreter/stdlib, real model startup and network latency.
They are not a before/after comparison; a baseline on the same machine is still needed.
The installed environment resolved OpenAI 3.28.0 and any-llm-sdk 1.33.0.

```bash
uv build
python scripts/minimal_install_smoke.py --report temp/minimal-install-metrics.json
```

## Remaining gates and rollback

249 offline regression cases passed; static checks, compilation, build and
minimal installation passed. Read the latest PR CI for the exact pushed revision.
Total package source remains 4,770 physical lines: the four-file core is 521
and the seven-file runtime mechanisms are 823. See the
[compatibility migration proposal](legacy-migration.md).

Native DeepSeek/Qwen/Claude live validation, larger coding tasks and comparable
baseline measurements remain open. Dynamic dependency recovery, long-term Memory,
Subagent and Streamable HTTP stay deferred. No main merge or release tag was created.
Rollback PRs in reverse dependency order and preserve sessions; do not replay
uncertain effects. Reverting the model-selection fix restores an unsafe implicit
default, so retain explicit model configuration when reverting unrelated changes.
