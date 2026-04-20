"""Shared registration metadata and context for tools and skills."""

from __future__ import annotations

import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class RegistrationScope:
    """Context describing the current registration source."""

    source: str = "runtime"
    pack_name: str = ""
    module: str = ""
    version: str = ""


@dataclass(frozen=True)
class RegistryMeta:
    """Metadata recorded for a registered tool or skill."""

    name: str
    source: str = "runtime"
    pack_name: str = ""
    module: str = ""
    version: str = ""


_DEFAULT_SCOPE = RegistrationScope()
_CURRENT_SCOPE: ContextVar[RegistrationScope] = ContextVar(
    "miniagent_registration_scope",
    default=_DEFAULT_SCOPE,
)


def get_registration_scope() -> RegistrationScope:
    """Return the active registration scope."""

    return _CURRENT_SCOPE.get()


@contextmanager
def registration_scope(
    source: str = "runtime",
    pack_name: str = "",
    module: str = "",
    version: str = "",
) -> Iterator[RegistrationScope]:
    """Temporarily override registration metadata for nested registrations."""

    current = get_registration_scope()
    scope = RegistrationScope(
        source=source or current.source,
        pack_name=pack_name or current.pack_name,
        module=module or current.module,
        version=version or current.version,
    )
    token = _CURRENT_SCOPE.set(scope)
    try:
        yield scope
    finally:
        _CURRENT_SCOPE.reset(token)


def infer_caller_module(*excluded: str) -> str:
    """Best-effort module inference for registration call sites."""

    excluded_modules = set(excluded)
    frame = inspect.currentframe()
    try:
        if frame is None:
            return ""
        caller = frame.f_back
        while caller is not None:
            module = inspect.getmodule(caller)
            module_name = getattr(module, "__name__", "")
            if (
                module_name
                and module_name not in excluded_modules
                and not module_name.startswith("importlib")
            ):
                return module_name
            caller = caller.f_back
    finally:
        del frame

    return ""


def build_registry_meta(name: str, module: str = "") -> RegistryMeta:
    """Build registry metadata from the active scope."""

    scope = get_registration_scope()
    return RegistryMeta(
        name=name,
        source=scope.source,
        pack_name=scope.pack_name,
        module=module or scope.module,
        version=scope.version,
    )
