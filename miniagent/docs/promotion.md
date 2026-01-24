# 零基础入门Agent！三分钟打造你的第一个AI助手🎉


宝子们，还在为不了解Agent原理发愁吗？还在为繁琐的配置头疼吗？今天给大家安利一个超宝藏的工具——[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)！三分钟，从零到一，轻松熟悉agent原理，打造属于你的AI助手！

为啥要选[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)呢？在AI飞速发展的今天，大语言模型（LLM）的能力简直逆天，但要让它们真正发挥价值，就需要AI Agent来帮忙。可现有的Agent框架，配置复杂、学习曲线陡峭、依赖特定LLM、工具集成困难，简直就是新手的噩梦。而[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)就是来拯救大家的！

看看[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)有多牛！
- **极简设计**：三分钟上手，零配置开箱即用，代码简洁明了，新手也能轻松搞定。
- **模型无关**：支持主流LLM，无需函数调用，统一接口设计，让你的AI助手更灵活。
- **工具自由**：轻松集成各种工具，自然语言调用，灵活扩展，想怎么用就怎么用。

用[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)打造AI助手超简单！三行代码就能搞定：
```python
from miniagent import MiniAgent

# 创建你的第一个Agent
agent = MiniAgent(
    model="deepseek-chat",
    api_key="your_api_key"
)

# 加载工具
agent.load_tools(["calculator", "web_search"])

# 运行Agent
response = agent.run("计算123 × 456并搜索最新的AI新闻")
print(response)
```

宝子们，[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)的实际应用超广泛，无论是快速原型开发、教学演示、自动化工作流还是智能助手开发，都能轻松搞定！快去试试吧！
- [访问GitHub](https://github.com/ZhuLinsen/MiniAgent)
- 安装依赖：`pip install -r requirements.txt`
- 运行示例：`python examples/simple_example.py`

[MiniAgent](https://github.com/ZhuLinsen/MiniAgent)让AI Agent开发不再是遥不可及的复杂技术。三分钟，从零到一，打造属于你的AI助手！家人们，赶紧试试吧！如果觉得不错，请给个star支持一下！


*标签*：#AI #Agent #LLM #开源 #MCP #ReAct #Tool Calling #MiniAgent #Python #人工智能 #开发工具 #新手友好