"""Minimal external pack example."""

PACK_NAME = "demo"
PACK_VERSION = "0.1.0"


def register():
    """Import tools and skills so MiniAgent can register them."""

    from . import skills, tools  # noqa: F401
