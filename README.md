# MiniAgent

🚀 **5分钟手搓一个 AI Coding 助手 + 命令行版 Manus！** | [English](README_EN.md)

<div align="center">
  <img src="resource/miniagent.png" alt="MiniAgent" width="400"/>

  [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
  [![GitHub stars](https://img.shields.io/github/stars/ZhuLinsen/MiniAgent?style=social)](https://github.com/ZhuLinsen/MiniAgent)
</div>

## 💡 核心特性

**一个 `agent.py` 核心文件，复刻 Claude Code 的编程能力 + Manus 的系统操控能力！**

MiniAgent 是一个**极简、透明、强大的 CLI Agent 框架**，拒绝臃肿的依赖和复杂的架构：

- 🧠 **Code Agent**: 像 Claude Code 一样写代码、修 Bug、跑测试
- 🦾 **OS Agent**: 像 Manus 一样操控浏览器、编辑文档、管理应用
- ⚡ **极简实现**: 核心引擎 `agent.py` 完全透明可控，适合学习和魔改
- 🤖 **全模型支持**: DeepSeek、OpenAI、Claude 等所有兼容 OpenAI 接口的模型
- 🔌 **高扩展性**: 极简装饰器模式，3行代码即可挂载自定义工具
- 🔄 **双模式工具调用**: 文本解析模式（透明可学习）+ 原生 Function Calling 模式（更可靠）
- 🎯 **Skill 系统**: 可复用的 Agent 配置，内置 coder/researcher/reviewer/tester 四个角色
- 🛡️ **安全防护**: 危险命令自动拦截确认，防止 LLM 幻觉导致破坏性操作
- 💬 **流式输出**: 打字机效果实时输出，长对话自动压缩上下文
- 🔗 **MCP 协议**: 支持连接 MCP 工具服务器，接入社区生态
- 🤝 **Agent 编排**: 内置编排器，支持任务分解 + 多角色协同

## 🤔 Why MiniAgent?

| | MiniAgent | smolagents | pydantic-ai | LangChain |
|---|---|---|---|---|
| **核心定位** | CLI Agent 教科书 | HuggingFace 生态 | 企业级类型安全 | 万能框架 |
| **核心代码** | 单文件可读 | ~1,000行 | 182MB | 10万+行 |
| **工具调用** | 文本解析 + 原生FC | Code Agent | 原生FC | 多层抽象 |
| **学习曲线** | ⭐ 30分钟上手 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **依赖** | 7个 | ~20个 | ~15个 | 50+ |
| **OS 控制** | bash 万能 | 需扩展 | 需扩展 | 需插件 |

> **MiniAgent 的独特价值：最好的 AI Agent 教科书。** 没有魔法、没有抽象，初学者可以完全理解 Agent 是如何工作的。

## 设计哲学

> **MiniAgent 不内置 100 个工具，而是用 6 个代码工具 + bash 实现无限可能。**

- 要截图？LLM 会 `bash: python -c "from mss import mss; mss().shot()"`
- 要控制鼠标？LLM 会 `bash: python -c "import pyautogui; pyautogui.click(100,200)"`
- 要爬网页？LLM 会 `bash: curl ... | python -c "..."`

这就是极简的力量：让 LLM 做它最擅长的事 — **思考和组合**。

## 快速开始

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git && cd MiniAgent
pip install -r requirements.txt && pip install -e .
cp .env.example .env  # 填入你的 API Key
miniagent              # 启动！
```

<details>
<summary>📋 详细安装说明</summary>

### 安装

```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
cd MiniAgent
pip install -r requirements.txt
pip install -e .  # 安装 miniagent 命令
```

### 配置

创建 `.env` 文件（参考 `.env.example`）：

```bash
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
```

### 运行

```bash
miniagent          # 或 python -m miniagent
```

</details>

## 命令行交互方式

MiniAgent 现在支持 3 种常用交互方式，适合人类直接使用，也适合脚本或机器人接入。

### 1. 交互式 REPL

最常见的用法就是直接进入 CLI 会话：

```bash
miniagent
# 或
python -m miniagent
```

常见启动参数：

```bash
python -m miniagent --config examples/config_example.json
python -m miniagent --config examples/config_example.json --profile demo_ops
python -m miniagent --pack examples.miniagent_demo_pack --skill demo_operator --tool demo_customer_lookup
python -m miniagent --model deepseek-chat --api-key <your-key> --base-url https://api.deepseek.com/v1
```

进入会话后，直接像聊天一样输入：

```text
you: compute 2+42
you: 帮我读取 README.md 前 50 行
you: 搜索项目里所有 TODO
```

内置常用命令：

```text
/help        显示帮助
/bootstrap   查看当前 profile/skill/tool 解析结果
/tools       查看当前已加载工具
/stream      切换流式输出
/mode        切换 text / native function calling
/model       临时切换模型
/clear       清空当前对话历史
/exit        退出
```

### 2. 命令行脚本化交互

如果你想在 shell 脚本里驱动 MiniAgent，可以直接通过标准输入喂命令：

```bash
printf 'compute 2+42\n/exit\n' | python -m miniagent --tool calculator --api-key <your-key> --model deepseek-chat
```

也可以用 Here-doc：

```bash
python -m miniagent --config examples/config_example.json <<'EOF'
帮我读取 README.md 前 20 行
/tools
/exit
EOF
```

这种方式适合：

- 本地 shell 自动化
- CI smoke test
- 用脚本批量验证某个 tool / profile 是否能启动

### 3. HTTP 控制面

如果你希望让外部机器人、测试器或自动化脚本稳定控制当前 MiniAgent 进程，可以开启 HTTP 控制面：

```bash
python -m miniagent --config langfuse_security_pack/profile.json --control-http 127.0.0.1:8765
```

可用接口：

```text
GET  /healthz
GET  /v1/session
GET  /v1/history?limit=20
POST /v1/message
POST /v1/interrupt   # 当前仅占位，未实现中断
```

非流式调用示例：

```bash
curl \
  -H 'Content-Type: application/json' \
  -d '{"text":"compute 2+42","stream":false,"mode":"text"}' \
  http://127.0.0.1:8765/v1/message
```

流式 NDJSON 调用示例：

```bash
curl -N \
  -H 'Content-Type: application/json' \
  -d '{"text":"compute 2+42","stream":true,"mode":"text","request_id":"req-1"}' \
  http://127.0.0.1:8765/v1/message
```

流式返回会按行输出事件，例如：

```json
{"type":"request.accepted","request_id":"req-1"}
{"type":"assistant.thinking","iteration":1}
{"type":"tool.start","name":"calculator","arguments":{"expression":"2 + 42"}}
{"type":"tool.end","name":"calculator","result":{"expression":"2 + 42","result":44}}
{"type":"assistant.final","content":"The result is 44."}
{"type":"request.complete","ok":true,"request_id":"req-1"}
```

如果你设置了：

```bash
export MINIAGENT_CONTROL_TOKEN=your-token
```

请求时需要带：

```bash
-H 'Authorization: Bearer your-token'
```

## 使用示例

```
you: 帮我创建一个 hello.py 文件
  ● write hello.py (1 lines)
    → ok
🤖 已创建 hello.py 文件！

you: 运行一下
  ● bash python hello.py
    → Hello World!
🤖 运行成功！
```

## ⚡ 演示

### 1. 操控浏览器搜索
> Prompt: "Open the browser, then search for 'zhulinsen/miniagent' on Google."

<img src="resource/miniagent_chrome.gif" alt="Browser Automation Demo" width="100%"/>

### 2. 自动化办公 (Word)
> Prompt: "Write a 500-word overview of AI agents in Word and format"

<img src="resource/miniagent_word.gif" alt="Word Creation Demo" width="100%"/>

### 3. 代码生成 (Coding)
> Prompt: "Create a ppo.py implementation and perform testing"

<img src="resource/miniagent_coding.png" alt="Coding Demo" width="100%"/>

## 内置工具

| 类别 | 工具 | 描述 |
|---|---|---|
| **Coding** | `read` | 读取文件内容 |
| | `write` | 创建/覆盖文件 |
| | `edit` | 编辑文件指定行 |
| | `grep` | 搜索文件内容 |
| | `glob` | 列出匹配的文件 |
| | `bash` | 执行 Shell 命令（支持超时控制） |
| **OS** | `open_browser` | 打开网页或搜索 |
| | `open_app` | 启动本地应用 (calc, notepad...) |
| | `create_docx` | 创建 Word 文档 |
| | `clipboard_copy`| 复制到剪贴板 |
| | `clipboard_read`| 读取剪贴板内容 |
| **System** | `system_info` | 系统信息 |
| | `system_load` | CPU/内存/磁盘负载 |
| | `process_list` | 进程列表 |
| | `disk_usage` | 磁盘使用情况 |
| | `env_get` | 读取环境变量 |
| | `env_set` | 设置环境变量 |
| **Misc** | `calculator` | 数学计算（AST 安全求值） |
| | `get_current_time` | 当前时间 |
| | `web_search` | 网页搜索 |
| | `http_request` | HTTP 请求 |
| | `file_stats` | 文件/目录统计 |

## 项目结构

```
miniagent/
├── agent.py        # 🧠 核心 Agent 引擎（从这里开始读！）
│                   #    LLM 循环 + 工具调用 + 上下文管理
├── cli.py          # 💬 交互式命令行界面（Rich + 流式输出）
├── tools/          # 🔧 工具集
│   ├── code_tools.py   # 代码工具 (read/write/edit/grep/glob/bash)
│   └── basic_tools.py  # 基础工具 (calculator/browser/clipboard/docx...)
├── extensions/     # 🔌 可选扩展
│   ├── mcp_client.py   # MCP 协议客户端
│   └── orchestrator.py # 多 Agent 编排器
├── skills.py       # 🎯 Skill 系统（可复用的 Agent 角色配置）
├── config.py       # ⚙️ 配置管理（.env + JSON + 环境变量）
├── memory.py       # 💾 轻量会话记忆
└── utils/          # 工具函数
    ├── json_utils.py   # 健壮 JSON 解析
    ├── text_utils.py   # 文本处理
    └── reflector.py    # 反思机制（可选）
```

## 双模式工具调用

MiniAgent 支持两种工具调用模式，便于学习和对比：

### 文本模式（默认）
LLM 在响应中输出结构化文本，Agent 解析执行 — **完全透明，最佳教学模式**：
```python
agent.run("计算 2+2")  # 默认文本模式
```

### 原生 Function Calling 模式
使用 OpenAI 兼容的 tools 参数 — **更可靠，支持并行工具调用**：
```python
agent.run("计算 2+2", mode="native")  # 原生 FC 模式
```

## MCP 协议支持

连接任意 MCP 工具服务器，一行代码接入社区生态：

```python
from miniagent import MiniAgent, load_mcp_tools

agent = MiniAgent(model="deepseek-chat", api_key="...")

# 加载 MCP 文件系统工具
for tool in load_mcp_tools("npx @anthropic/mcp-server-filesystem /tmp"):
    agent.add_tool(tool)
```

## Agent 编排

内置编排器，自动分解复杂任务并分配给专业 Worker（基于 Skill 系统）：

```python
from miniagent import Orchestrator

orch = Orchestrator(model="deepseek-chat", api_key="...", base_url="...")
result = orch.run("研究 Python 异步模式，写一个 demo 并测试")
# 自动规划: researcher → coder → tester
```

## Skill 系统

Skill 是可复用的 Agent 配置：prompt + 工具白名单 + 参数。内置 4 个 Skill，也可自定义：

```python
from miniagent import MiniAgent, Skill, register_skill

# 使用内置 Skill
agent = MiniAgent(model="deepseek-chat", api_key="...", base_url="...")
agent.load_all_tools()
agent.load_skill("coder")  # 自动设置代码专家 prompt + 只保留代码工具

# 自定义 Skill
register_skill(Skill(
    name="devops",
    prompt="You are a DevOps engineer. Focus on CI/CD, Docker, and infrastructure.",
    tools=["bash", "read", "write"],
    temperature=0.3,
))
```

## 外挂 Pack 与部署 Profile

业务专属 `tool/skill` 可以继续放在独立 Python 包里，MiniAgent 只负责加载和解析最终启用集，不需要改动内置目录结构。

如果是你本地业务专用的 pack，建议直接放在仓库根目录的 `*_pack/` 文件夹中，例如 `langfuse_security_pack/`。
这类目录默认可以通过 `.gitignore` 忽略，避免在提交 MiniAgent 架构代码时把具体业务 pack 一起上传。

```python
# examples/miniagent_demo_pack/pack.py
PACK_NAME = "demo"
PACK_VERSION = "0.1.0"

def register():
    from . import tools, skills
```

```json
{
  "packs": ["examples.miniagent_demo_pack"],
  "profile": "demo_ops",
  "profiles": {
    "default": {
      "tools": ["read", "write", "edit", "bash", "grep", "glob"],
      "skill": "coder"
    },
    "demo_ops": {
      "packs": ["examples.miniagent_demo_pack"],
      "tools": ["read", "grep", "bash", "demo_customer_lookup"],
      "skill": "demo_operator"
    }
  }
}
```

CLI 可以显式切换：

```bash
miniagent --config examples/config_example.json --profile demo_ops
miniagent --pack examples.miniagent_demo_pack --skill demo_operator --tool demo_customer_lookup
```

如果系统发生隐式行为，比如 “未显式配置 tools，回退到 skill 白名单” 或 “skill 过滤掉了 profile 请求的 tool”，启动时会直接打印 bootstrap warnings，不会静默处理。

## 自定义工具

```python
from miniagent import MiniAgent
from miniagent.tools import register_tool

@register_tool
def my_tool(arg: str) -> str:
    """我的自定义工具"""
    return f"处理: {arg}"

agent = MiniAgent(...)
agent.load_builtin_tool("my_tool")
```

## 与同类项目对比

| 特点 | MiniAgent | smolagents | pydantic-ai | LangChain |
|------|-----------|-----------|------------|-----------|
| 核心代码 | 单文件可读 | ~1,000行 | 182MB | 10万+行 |
| 工具调用 | 文本解析 + 原生FC 双模式 | Code Agent | 原生FC | 多层抽象 |
| 可读性 | ⭐⭐⭐⭐⭐ 初学者友好 | ⭐⭐⭐⭐ 紧凑 | ⭐⭐⭐ 企业级 | ⭐⭐ 复杂 |
| OS 控制 | bash 万能 + 专用工具 | 需扩展 | 需扩展 | 需插件 |
| 教学价值 | 最好的 Agent 教科书 | HuggingFace 生态强 | 类型安全最佳 | 过于复杂 |
| 模型支持 | 全模型兼容 | 全模型 | 全模型 | 全模型 |
| Skill 系统 | ✅ 内置 | ❌ | ❌ | ❌ |
| MCP 支持 | ✅ | ❌ | ✅ | 需插件 |

## 致谢

MiniAgent 的 Code Tools 设计参考了 [nanocode](https://github.com/1rgs/nanocode) 项目，感谢其优雅的极简实现思路！

## 许可证

[Apache License 2.0](LICENSE)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
