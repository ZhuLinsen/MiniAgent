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

## 设计资产

维护者选择了 A 方向：延续作者 AlphaEvo 的暖色终端风格。可编辑资产为 [横幅](assets/miniagent-banner.svg) 与 [独立图标](assets/miniagent-icon.svg)，没有外部字体下载或动画。横幅用于 README，图标可用作头像。

三张 AI 概念稿和生成提示词保存在本地 `temp/brand-review/`，不作为真实产品截图入库。最终 SVG 是按选定方向重新绘制的矢量源文件，可在此基础上继续调整。
