# 真实 CLI 演示 / Real CLI capture

## 记录说明

2026-10-17，Windows、Python 3.12.10、MiniAgent `0.3.0a1`。运行版本为原生精简提交 [`3bb2f20`](https://github.com/ZhuLinsen/MiniAgent/commit/3bb2f20b444a441337b19cf13724e5c233c388d7)，各包源文件 SHA-256 保存在元数据中。模型为 Anspire 网关的 `qwen3.5-flash`，通过自定义 OpenAI-compatible 连接调用。

截图来自 `scripts/capture_terminal.py` 对真实 CLI Rich Console 的记录：只替换输出接收端，不替换模型、工具或授权。原始内容：[文本](assets/coding-session.txt)、[SVG](assets/coding-session.svg)、[脱敏运行元数据](assets/coding-session.json)。PNG 由 SVG 栅格化；未重写回答、补画工具结果或模拟 API。

The screenshot renders a real CLI recording. Only the output sink is replaced; the provider, tools, policy and session remain real. It shows a deliberately small function repair, not broad coding-agent benchmark evidence.

## 任务与结果

- 初始 `calculator.py` 错误地使用 `return a - b`。
- Agent 读取源文件和测试文件，然后调用 `edit`、`bash`，把减法改为加法并执行 `python -m unittest -v`。
- 测试包含两个断言；调用模型前独立运行确认失败，修复后再独立运行确认通过，并对比 SHA-256 确认测试文件未改动。
- 修复共 4 次模型请求、5,545 tokens。关闭 CLI 后用同一 JSONL 路径续接，再用 1 次请求、1,622 tokens 正确回忆修改和测试结果；两轮合计 7,167 tokens，没有测量或推断金额。
- [续接原始输出](assets/coding-resume.txt)与元数据记录了第二轮结果；两轮共 2 条用户消息，全部工具结果配对，没有重放工具或留下不确定调用。
- 此次截取使用 `--no-stream`，便于完整保留 Markdown 最终回答。流式协议另有回归与历史真实验收。
- 本地验收限制每次输出最多 700 tokens、每次请求 40 秒、最多 6 次请求；这是本次验收保护，不是生产 CLI 的默认限额。

## 复现

1. 按 README 安装，运行 `miniagent --connect` 配置自己的连接。模型目录和输出可能随供应商变化。
2. 创建全新的演示目录；脚本遇到已有目录会拒绝覆盖：

```bash
python scripts/prepare_demo.py demo-workspace
```

3. 使用自有配置运行下面的命令。`trusted` 会允许这个隔离演示目录中的文件修改和 Shell 调用；平时可使用默认确认策略。

```bash
python scripts/capture_terminal.py --output demo-capture -- --workspace demo-workspace --policy trusted --no-stream --prompt "Read calculator.py. Fix add using the edit tool, then run python -m unittest -v with bash. Do not modify test_calculator.py. Summarize the fix and test result in two short lines."
```

命令会实际调用你的供应商并产生用量，输出 `demo-capture.txt` 和 `demo-capture.svg`。用浏览器打开 SVG，或用现有 SVG 渲染工具转 PNG；生产包不新增图像依赖。不要复用包含私有数据的工作区录制公开演示。

4. 在 `demo-workspace` 复跑 `python -m unittest -v`，检查只修复了 `calculator.py`。

5. 使用首次会话对应的 JSONL 路径（交互中可用 `/session` 查看完整路径）续接，检查能否回忆上一轮，不再次运行工具：

```bash
miniagent --session <session-jsonl-path> --workspace demo-workspace --no-stream --prompt "Without calling any tools, briefly recall which function you fixed and the test result from our previous turn."
```

## 终端动态回放

首页的 `coding-replay.gif` 根据本分支已有的 `coding-session.txt` 逐段绘制，保留原始提示、工具顺序和回答；统一调整播放间隔，末帧停留 4.5 秒。因此它是实录的动态回放，不是本轮重新调用模型或录制桌面，也不用于展示实际响应速度。原始文本、静态 PNG 和运行元数据仍可查看。

复现渲染时，在独立工具环境安装 Pillow，并指定本机等宽字体；Pillow 不加入 MiniAgent 的运行依赖：

```bash
python -m pip install Pillow
python scripts/render_terminal_replay.py docs/assets/coding-session.txt demo-replay.gif --font path/to/monospace.ttf
```

Windows 可以将字体参数写成 `--font consola.ttf`。脚本只读取文本，不调用模型，不修改任务结果。要重新执行真实任务，使用上面的 `capture_terminal.py` 命令录制自己的输出，再传给渲染脚本。

The GIF replays the existing real CLI transcript with edited timing. It is not a new model run, a desktop screen recording, or a latency measurement. Rendering uses optional Pillow tooling; the agent runtime is unchanged.

## Windows 案例

README 中的浏览器与 Word GIF 是项目原版的 Windows 实录，文件分别为 `resource/miniagent_chrome.gif`、`resource/miniagent_word.gif`；本轮恢复展示，未重新录制或修改图像。录屏对应旧版工具入口，不能当作原生 0.3 的 GUI 回归结果。

原生 CLI 保留 `bash` 工具，在 Windows 上使用本机 Shell 执行命令。它可以调用 Python 脚本、本机程序或安装的自动化工具；默认工具集不包含 `open_browser`、`open_app`、`create_docx` 等旧工具。旧版仍可使用 [归档分支](legacy-migration.md)。

### 打开浏览器

运行 `miniagent`，输入：

> 使用 Python 标准库 webbrowser 打开默认浏览器，在 Google 搜索 MiniAgent 的 GitHub 仓库。

打开网页可使用 Python [webbrowser 标准库](https://docs.python.org/3/library/webbrowser.html)调用系统默认浏览器；继续点击网页、读取页面或操作表单，需要配置浏览器自动化脚本或相应 MCP 服务。当前工具集没有内置视觉识别或鼠标定位。

### 生成 Word 文档

生成 `.docx` 文件可在 MiniAgent 使用的 Python 环境安装相应库，例如 [python-docx](https://python-docx.readthedocs.io/en/latest/user/install.html)：

```bash
python -m pip install python-docx
miniagent
```

然后输入：

> 使用 Python 生成一篇 500 字的 AI Agent 介绍，保存为 agent-intro.docx，包含标题、小节和正文。完成后检查文件是否生成。

生成文档文件不要求安装 Microsoft Word；在 Word 窗口内点击、输入和排版则需要已安装的 Word、可交互的 Windows 桌面及相应自动化依赖。桌面点击和键盘操作可以通过自己配置的脚本或 MCP 服务接入，不是安装 MiniAgent 后自带的 GUI 工具。

这些任务需要执行 Shell 或写入文件，不能在 `--policy readonly` 下运行。使用默认交互模式，先查看命令再确认；非交互模式不会替你确认。原生版尚未重跑上述浏览器和 Office 的完整桌面流程。

The two Windows GIFs in the README are original-version recordings. The native CLI uses local Shell/Python or configured MCP tools; document generation and GUI interaction require their own dependencies. These recordings do not claim a fresh native-version GUI validation.

## 设计资产

维护者选择了 A 方向：延续作者 AlphaEvo 的暖色终端风格。可编辑资产为 [横幅](assets/miniagent-banner.svg) 与 [独立图标](assets/miniagent-icon.svg)，没有外部字体下载或动画。横幅用于 README，图标可用作头像。

三张 AI 概念稿和生成提示词保存在本地 `temp/brand-review/`，不作为真实产品截图入库。最终 SVG 是按选定方向重新绘制的矢量源文件，可在此基础上继续调整。
