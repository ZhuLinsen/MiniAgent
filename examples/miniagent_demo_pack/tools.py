"""Domain-specific tools for the demo external pack."""

from miniagent.tools import register_tool


@register_tool
def demo_customer_lookup(customer_id: str) -> str:
    """Return a fake customer summary for pack-loading demos."""

    return f"Customer {customer_id}: active plan, region=apac, status=ok"
