# MiniAgent

- 🚀「Build Your First LLM Agent in 5 Minutes!」 ⚡️ Build an LLM agent from scratch in 5 minutes! | [中文版本](README.md)
    

<div align="center">
  <img src="miniagent.png" alt="MiniAgent" width="600"/>
</div>


## Why Do We Need AI Agents?

In the rapidly evolving world of Large Language Models (LLMs), we've witnessed their remarkable capabilities. However, to truly unleash their potential, we need to enable them to interact with tools and environments - this is where AI Agents come into play.

For beginners, understanding Agent principles and implementing one can be a daunting task. Complex frameworks, tedious configurations, and steep learning curves often deter newcomers. This is why we created **MiniAgent**.

## Create Your First Agent in 3 Minutes

Let me show you how to create your first AI Agent in just three minutes:

```python
from miniagent import MiniAgent

# Create your first Agent
agent = MiniAgent(
    model="deepseek-chat",
    api_key="your_api_key"
)

# Load tools
agent.load_tools(["calculator", "web_search"])

# Run Agent
response = agent.run("Calculate 123 × 456 and search for the latest AI news")
print(response)
```

Yes, it's that simple! Three lines of code, and you have a fully functional AI Agent that can perform calculations and web searches.

## Why Choose MiniAgent?

1. **Rapid Learning**: Perfect starting point for understanding Agent principles
2. **Model Agnostic**: Works with any LLM, even without function calling support
3. **Minimalist Design**: Clean, readable code focused on core functionality
4. **Lightweight**: No heavy dependencies, easy to integrate and extend

## Key Features

- **Multiple LLM Support**: Compatible with OpenAI, DeepSeek, Anthropic, and more
- **Simple Tool Integration**: Easy tool registration through natural language
- **No Function Calling Required**: Works with any LLM
- **Response Reflection**: Optional mechanism to improve answer quality
- **Environment-based Config**: Simple configuration via .env files
- **Fast Learning Curve**: Ideal for learning Agent concepts
- **LLM Validation Tool**: Built-in API verification

## Practical Example

Let's create a text analysis Agent:

```python
@register_tool
def text_analyzer(text: str) -> Dict:
    """Analyze text content"""
    return {
        "character_count": len(text),
        "word_count": len(text.split()),
        "sentence_count": len([s for s in text.split('.') if s.strip()])
    }

agent = MiniAgent()
agent.tools.append(text_analyzer)
response = agent.run("Analyze this text: 'AI is changing the world.'")
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/ZhuLinsen/MiniAgent.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env file with your API keys
```

4. Run examples:
```bash
python examples/simple_example.py
```

## Join the Community

MiniAgent is an open-source project, and we welcome all contributors! Whether you want to submit code, report issues, or share experiences, your contributions are valuable.

If you find this project helpful, don't forget to give it a ⭐️! Your support drives us to keep improving.

## Conclusion

AI Agents are no longer complex technologies out of reach. With MiniAgent, anyone can quickly understand Agent principles and create their own AI assistant.

Remember: From zero to hero in just three minutes.

---

If you like this article:
1. Give MiniAgent a ⭐️
2. Share it with friends interested in AI Agents
3. Share your experience in the comments

Let's push the boundaries of AI Agents together! 🚀

---

*The author is one of the developers of MiniAgent, dedicated to making AI technology more accessible and user-friendly.* 