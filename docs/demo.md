# MiniAgent 演示说明 / Demo notes

## 终端任务回放

首页动图来自 2026-10-17 的真实 CLI 任务记录：Windows、Python 3.12、MiniAgent 0.2.0a1。运行基于 main `64c1fcb`，加入展示分支的终端样式；该样式尚未进入主线。记录与素材保留于[原提交](https://github.com/ZhuLinsen/MiniAgent/tree/634b94ec8d9c55b8270807e8387f74ec3beb4de4)。

Agent 读取有错误的 `calculator.py`，将加法函数中的减法修正，再执行原有单元测试。模型之外另跑一次测试确认通过，测试文件 SHA-256 保持不变。此次运行调用真实模型和工具，使用 Anspire 网关的 `qwen3.5-flash`，共 4 次请求、5,068 tokens。

- [原始终端文本](assets/coding-session.txt)
- [运行元数据](assets/coding-session.json)
- [静态 PNG](assets/coding-session.png) / [SVG](assets/coding-session.svg)

GIF 根据原始文本逐段绘制，保留提示、工具顺序和回答，压缩了播放间隔。这是一项小型函数修复演示，不是响应速度或复杂仓库任务的基准测试。

The GIF replays a real CLI task recorded on the presentation branch, based on main `64c1fcb`. Its terminal styling is not yet part of main. Playback timing is condensed; the transcript, tool results and model answer are preserved. This is a small repair example, not a latency or coding benchmark.

## 复现任务

按 README 安装并连接模型，在新的工作目录创建下面两个文件。

`calculator.py`：

```python
def add(a, b):
    return a - b
```

`test_calculator.py`：

```python
import unittest
from calculator import add

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 2), 1)
```

在该目录运行 `python -m unittest -v`，确认测试失败。然后启动 `miniagent`，输入：

> 读取 calculator.py，修复 add 函数并运行 python -m unittest -v。不要修改 test_calculator.py。说明修改内容和测试结果。

按交互提示确认文件修改和命令执行。完成后独立运行同一条测试命令，并核对测试文件未被修改。实际模型输出可能不同。

原录制使用的[任务准备脚本](https://github.com/ZhuLinsen/MiniAgent/blob/634b94ec8d9c55b8270807e8387f74ec3beb4de4/scripts/prepare_demo.py)、[终端录制脚本](https://github.com/ZhuLinsen/MiniAgent/blob/634b94ec8d9c55b8270807e8387f74ec3beb4de4/scripts/capture_terminal.py)和[回放渲染脚本](https://github.com/ZhuLinsen/MiniAgent/blob/634b94ec8d9c55b8270807e8387f74ec3beb4de4/scripts/render_terminal_replay.py)保留在对应提交。

To repeat the task, create the two files above in a new directory, confirm that the tests fail, then ask MiniAgent to fix `add` without changing the test file. Approve the proposed edits and commands, rerun the tests independently, and verify that the test file is unchanged. Recording and rendering scripts are linked to their original revision.

## Windows 案例

首页的浏览器与 Word GIF 来自项目原版 Windows 实录。本次保留原图，未重新录制；它们不代表当前原生 CLI 的完整桌面回归结果。

当前原生 CLI 可通过 Shell 调用 Python、本机程序或配置好的 MCP 工具。浏览器操作可以使用 Python 的 `webbrowser` 打开网页；进一步点击、读取页面或操作表单，需要相应的自动化脚本或 MCP 服务。

生成 Word 文件可以安装 `python-docx`，再让 Agent 编写脚本生成 `.docx`。直接操作 Word 窗口则需要已安装的 Word、可交互桌面和相应自动化依赖。旧版工具入口见[迁移说明](legacy-migration.md)。

These Windows GIFs are original-version recordings. The native CLI calls local Python/Shell programs or configured MCP tools; browser interaction and Word automation need their own software and dependencies. The recordings are not a fresh native-CLI desktop validation.
