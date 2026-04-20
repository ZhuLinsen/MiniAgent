"""External pack loading for skills and tools."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .diagnostics import BootstrapReport
from .logger import get_logger
from .registration import registration_scope
from .skills import list_skills
from .tools import get_registered_tools

logger = get_logger(__name__)


@dataclass
class PackLoadResult:
    """Result of loading one external pack."""

    spec: str
    pack_name: str
    version: str = ""
    module: str = ""
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)


_LOADED_PACKS: Dict[str, PackLoadResult] = {}


def _emit(report: Optional[BootstrapReport], code: str, level: str, message: str) -> None:
    """Log and optionally record a bootstrap diagnostic."""

    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)

    if report is not None:
        report.add(code, level, "both", message)


def _snapshot_registry() -> Tuple[Set[str], Set[str]]:
    """Capture current registered tool and skill names."""

    return set(get_registered_tools().keys()), set(list_skills())


def _resolve_entry_module(spec: str) -> Optional[str]:
    """Resolve a pack spec to an importable entry module."""

    candidates = ["%s.pack" % spec, spec]
    for candidate in candidates:
        try:
            found = importlib.util.find_spec(candidate)
        except (ModuleNotFoundError, ValueError):
            found = None
        if found is not None:
            return candidate
    return None


def get_loaded_packs() -> Dict[str, PackLoadResult]:
    """Return loaded external packs keyed by requested spec."""

    return _LOADED_PACKS


def clear_loaded_packs() -> None:
    """Clear the in-memory loaded-pack cache."""

    _LOADED_PACKS.clear()


def load_pack(
    spec: str,
    *,
    strict: bool = False,
    report: Optional[BootstrapReport] = None,
) -> PackLoadResult:
    """Load one external pack by explicit module spec."""

    if spec in _LOADED_PACKS:
        _emit(report, "R012", "warning", "Pack '%s' was already loaded; skipping." % spec)
        return _LOADED_PACKS[spec]

    entry_module = _resolve_entry_module(spec)
    if not entry_module:
        message = "Pack '%s' could not be found." % spec
        _emit(report, "R003", "error" if strict else "warning", message)
        return PackLoadResult(spec=spec, pack_name=spec)

    before_tools, before_skills = _snapshot_registry()
    try:
        with registration_scope(source="pack", pack_name=spec, module=entry_module):
            module = importlib.import_module(entry_module)

        pack_name = str(getattr(module, "PACK_NAME", spec) or spec)
        pack_version = str(getattr(module, "PACK_VERSION", "") or "")
        register = getattr(module, "register", None)
        if callable(register):
            with registration_scope(
                source="pack",
                pack_name=pack_name,
                module=entry_module,
                version=pack_version,
            ):
                manifest = register()
            if isinstance(manifest, dict):
                pack_name = str(manifest.get("name") or pack_name)
                pack_version = str(manifest.get("version") or pack_version or "")
    except Exception as exc:
        message = "Failed to load pack '%s': %s" % (spec, exc)
        _emit(report, "R003", "error" if strict else "warning", message)
        return PackLoadResult(spec=spec, pack_name=spec, module=entry_module)

    after_tools, after_skills = _snapshot_registry()
    result = PackLoadResult(
        spec=spec,
        pack_name=pack_name,
        version=pack_version,
        module=entry_module,
        tools=sorted(after_tools - before_tools),
        skills=sorted(after_skills - before_skills),
    )
    _LOADED_PACKS[spec] = result

    if report is not None and spec not in report.packs_loaded:
        report.packs_loaded.append(spec)

    return result


def load_packs(
    specs: List[str],
    *,
    strict: bool = False,
    report: Optional[BootstrapReport] = None,
) -> List[PackLoadResult]:
    """Load a list of explicit pack specs."""

    results: List[PackLoadResult] = []
    if report is not None:
        for spec in specs:
            if spec not in report.packs_requested:
                report.packs_requested.append(spec)

    for spec in specs:
        results.append(load_pack(spec, strict=strict, report=report))

    return results
