# AGENTS.md — MiniAgent 项目指南

## 项目定位

MiniAgent 是一个**极简、透明、强大的 CLI Agent 框架**。

**一句话描述**：用 ~400 行核心函数，实现 Claude Code 的编程能力 + Manus 的系统操控能力。

## 核心原则

### 1. 极简即力量
- 核心 Agent 逻辑控制在 ~400 行，初学者 30 分钟可读完
- 不追求工具数量，追求 `bash + LLM 智能` 的无限组合能力
- 每一行代码都应该有存在的理由

### 2. 透明可控
- 工具调用过程完全可见（TOOL: xxx ARGS: {...}）
- 没有黑盒抽象，没有魔法
- 初学者可以清楚看到 AI Agent 是怎么工作的

### 3. bash 是万能工具
- MiniAgent 不内置 100 个专用工具，而是依赖 bash + LLM 的组合
- 要截图？LLM 会通过 bash 调用 `python -c "from mss import mss; mss().shot()"`
- 要控制鼠标？LLM 会通过 bash 调用 pyautogui
- 要爬网页？LLM 会通过 bash 编写并运行 Python 脚本
- 这种设计让框架保持极简，同时能力无上限

### 4. 教学优先
- 这是"最好的 AI Agent 教科书"
- 代码结构清晰：agent.py（核心循环）→ tools/（工具集）→ cli.py（交互界面）
- 支持文本解析和原生 Function Calling 两种模式，便于对比学习

### 5. 不做大杂烩
- 不引入重型依赖（pyautogui/playwright/mss 等不作为内置依赖）
- 不增加不必要的抽象层
- 如果一个功能可以通过 bash 实现，就不为它单独建工具

## 架构概览

```
miniagent/
├── agent.py        # 核心 Agent 循环（~400行核心函数）
│                   # - LLM 客户端初始化
│                   # - 工具调用解析（文本模式 + 原生 FC 模式）
│                   # - 流式输出 (_call_llm_stream)
│                   # - 上下文管理 (_summarize_messages)
│                   # - 危险命令检测 (_check_dangerous)
│                   # - 工具执行循环
│                   # - 消息历史管理
├── cli.py          # 交互式命令行界面
│                   # - Rich 美化输出
│                   # - 流式 token 输出
│                   # - 工具执行回调显示
│                   # - 危险命令 Rich 确认弹窗
│                   # - 会话记忆集成
├── config.py       # 配置管理（.env / JSON / 环境变量）
├── logger.py       # 日志配置
├── memory.py       # 轻量会话记忆（~/.miniagent/memory.json）
├── mcp_client.py   # MCP 客户端 re-export（→ extensions/）
├── orchestrator.py # Agent 编排器 re-export（→ extensions/）
├── skills.py       # Skill 系统（可复用的 Agent 配置）
│                   # - name + prompt + tool whitelist + temperature
│                   # - 内置: coder/researcher/reviewer/tester
├── extensions/
│   ├── mcp_client.py   # MCP 协议客户端实现
│   │                   # - stdio JSON-RPC 传输
│   │                   # - 工具发现 + 调用
│   │                   # - 自动转为 MiniAgent 工具格式
│   └── orchestrator.py # Agent 编排器实现
│                       # - 任务分解（planner agent）
│                       # - 角色分配（基于 Skill 系统）
│                       # - 上下文传递
├── tools/
│   ├── __init__.py     # 工具注册系统（@register_tool 装饰器）
│   ├── code_tools.py   # 代码工具：read/write/edit/grep/glob/bash
│   └── basic_tools.py  # 基础工具：calculator/time/system/browser/clipboard/docx
└── utils/
    ├── json_utils.py   # 健壮的 JSON 解析（处理 LLM 输出的各种格式问题）
    ├── text_utils.py   # 共享文本工具（smart_truncate）
    └── reflector.py    # 反思机制（可选，用于改善推理质量）
```

## Agent 核心循环

```
用户输入
  ↓
构建系统提示（含可用工具描述）
  ↓
调用 LLM
  ↓
解析响应 → 包含工具调用？
  ├─ 是 → 执行工具 → 结果回传 → 再次调用 LLM（循环）
  └─ 否 → 返回最终响应
```

## 工具调用方式

### 文本模式（默认，教学友好）
LLM 在响应中输出结构化文本，Agent 用正则解析：
```
TOOL: bash
ARGS: {"cmd": "ls -la"}
```

### 原生 Function Calling 模式（可选，更可靠）
使用 OpenAI 兼容的 `tools` 参数，模型返回结构化 `tool_calls`。
通过 `mode="native"` 启用。

## 自定义工具

```python
from miniagent.tools import register_tool

@register_tool
def my_tool(arg: str) -> str:
    """我的自定义工具"""
    return f"处理: {arg}"
```

3 行代码即可注册一个新工具。Agent 会自动从函数签名和 docstring 生成工具描述。

## 贡献原则

1. **保持简单** — 新增代码需要有充分理由，优先用现有工具（尤其是 bash）解决问题
2. **不破坏现有功能** — 所有改动需确保向后兼容
3. **测试覆盖** — 核心逻辑改动需附带测试
4. **中英文** — README 维护中英文两个版本

## 测试

```bash
python -m pytest tests/ -v
```

当前测试覆盖：100+ 测试用例，涵盖工具注册、JSON 解析、技能系统、会话记忆、Agent 初始化等。

## Git 工作流

- **禁止直接 push 到 main 分支**，所有改动需通过 Pull Request 提交
- PR 需要至少一位 maintainer 审核同意后才能合并
- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式（`feat:`, `fix:`, `refactor:`, `docs:` 等）
- 涉及核心逻辑（agent.py, tools/）的改动需附带测试

## 可配置参数

以下限制参数可通过环境变量或 `.env` 文件覆盖：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LLM_API_KEY` | — | LLM API 密钥（必需） |
| `LLM_MODEL` | — | 模型名称（必需） |
| `LLM_API_BASE` | — | API 基础 URL |
| `LLM_TEMPERATURE` | 0.7 | LLM 采样温度 |
| `LLM_ORGANIZATION` | — | OpenAI organization ID |
| `BASH_TIMEOUT` | 120 | bash 工具默认超时时间（秒） |
| `BASH_MAX_OUTPUT` | 50000 | bash 输出最大字符数 |
| `TOOL_RESULT_LIMIT` | 16000 | 工具结果回传给 LLM 的最大字符数 |
| `MAX_CONTEXT_MESSAGES` | 20 | 超过此数量自动压缩对话历史 |
| `CONFIRM_DANGEROUS` | true | 是否拦截危险 bash 命令 |
| `MINIAGENT_STREAM` | 1 | 是否启用流式输出（0=关闭） |
| `ENABLE_REFLECTION` | false | 是否启用反思机制 |
| `REFLECTION_MAX_ITERATIONS` | 3 | 反思最大迭代次数 |
| `SERPAPI_KEY` | — | SerpAPI 密钥（web_search 工具需要） |
| `LOG_LEVEL` | INFO | 日志级别 |
| `MINIAGENT_HOME` | ~/.miniagent | 会话记忆存储路径 |

**多供应商别名**: 如果未设置 `LLM_API_KEY`，框架会依次尝试读取 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`ANTHROPIC_API_KEY`、`AZURE_OPENAI_API_KEY` 作为 fallback。详见 `config.py`。

超出限制时使用**头+尾智能截断**（保留 70% 开头 + 30% 结尾），确保错误信息不会因截断丢失。

bash 工具的 `timeout` 参数也可在每次调用时由 LLM 自行指定，例如对安装类命令传入 `timeout=300`。
