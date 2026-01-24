# 🔥DeepSeek加持！手搓“平替版”Manus，电脑操控+AI编程全搞定！

🎉 **别再只有羡慕的份了！不用排队等Manus，200行Python代码教你手搓一个命令行版！**

最近 Manus 和 Claude Code 火得不要不要的，一个能操控电脑，一个能自动写代码。
但你知道吗？其实核心原理并不复杂！

今天给大家安利一个超硬核的开源项目——**[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)**！
它不仅仅是一个 AI Coding 助手，现在更升级了 **OS 操控能力**，妥妥的“命令行版 Manus”！

## 🌟 为什么它能当“平替”？

1.  **AI Coding 能力**：像 Claude Code 一样，它在终端里就能帮你写代码、改Bug、读文件、跑测试。
2.  **电脑操控能力（新！）**：
    *   🌍 **自动上网**：让它“帮我查一下最新的AI新闻”，自动打开浏览器搜索。
    *   📂 **办公自动化**：让它“整理这篇周报生成Word”，直接生成 .docx 文件。
    *   🚀 **启动应用**：让它“打开计算器”或“打开记事本”，应用秒开。
    *   📋 **剪贴板管理**：复制粘贴，它都能帮你搞定。

## 🛠️ 怎么做到的？

核心代码不到 500 行！完全开源透明，你可以清楚地看到它是如何：
*   用 `Tool Calling` 驱动本地 Python 函数
*   用 `subprocess` 执行系统命令
*   用 `Playwright`/`Webbrowser` 操控网页

**这才是真正的“可控 AI”！没有黑盒，自己魔改！**

## ⚡ 三行代码上手

```python
from miniagent import MiniAgent

# 1. 配置你的 LLM (DeepSeek, OpenAI, Claude 均可)
agent = MiniAgent(model="deepseek-chat", api_key="sk-...")

# 2. 跑起来！
agent.run("帮我查一下今天的GitHub热榜，并整理成一个Word文档发到桌面上")
```

## 🌈 适合谁？
*   想学习 Agent 原理的开发者（最好的教科书！）
*   嫌重型 IDE 插件太慢，喜欢极客风 CLI 的程序员
*   想打造自己专属“贾维斯”的 DIY 达人

👉 **项目地址**：[https://github.com/ZhuLinsen/MiniAgent](https://github.com/ZhuLinsen/MiniAgent)
⭐ **求个 Star！一起探索 AI Agent 的无限可能！**

*标签*：#AI #Agent #Manus #ClaudeCode #DeepSeek #Python #开源 #黑科技 #编程助手 #自动化
