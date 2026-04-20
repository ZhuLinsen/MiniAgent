"""Domain-specific skills for the demo external pack."""

from miniagent.skills import Skill, register_skill


register_skill(Skill(
    name="demo_operator",
    prompt=(
        "You are a demo operations agent. Prefer the demo customer lookup tool "
        "for customer-specific questions and use read-only common tools when needed."
    ),
    tools=["read", "grep", "bash", "demo_customer_lookup"],
    temperature=0.2,
    description="Demo external-pack operator",
))
