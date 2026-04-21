"""External pack for Langfuse security analysis."""

PACK_NAME = "langfuse_security"
PACK_VERSION = "0.1.0"


def register():
    """Import tools and skills so MiniAgent can register them."""

    from . import skills, tools  # noqa: F401
