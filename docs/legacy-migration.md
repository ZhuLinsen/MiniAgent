# v0.3 compatibility migration proposal

This is a removal plan for review, not an implemented breaking release.
v0.2.0a1 retains the existing `MiniAgent` API and `--legacy` entry point.

## Inventory and proposed replacements

| Retained implementation | Physical lines | Proposed migration |
| --- | ---: | --- |
| `legacy.py` and `legacy_cli.py` | 1,169 | Migrate callers to Harness and native CLI; decide support window before removal. |
| `tools/basic_tools.py` | 682 | Move optional system tools to an independently installed plugin package. |
| `utils/json_utils.py` | 304 | Remove text-tool parsing only after native-tool callers have migrated. |
| `utils/reflector.py` | 197 | Replace with an explicitly installed plugin only if real users need it. |
| `extensions/orchestrator.py` | 194 | Keep deferred; design a separate extension rather than enlarge the kernel. |

Counts come from `python scripts/source_stats.py` on the current working tree.
These modules are coupled: subtracting their counts does not prove that the
remaining package builds or preserves public imports. Check wrappers, exports,
registry initialization, example usage and dependency metadata together.

## Removal gates

1. Document public import/CLI replacements and announce the compatibility window.
2. Move optional tools with tests and a working installation path before deleting them.
3. Remove unused exports and dependencies; build and install the resulting wheel
   outside the checkout. Retest plugin lifecycle, authorization and session restore.
4. Repeat source counts and the same installation/startup measurements on the
   same machine; record both revisions and dependency versions.
5. Validate real provider task traces before declaring stable v0.3. Current
   Anspire gateway evidence does not establish native Claude API compatibility.

The 2,000–2,800 total-source target remains unfulfilled at 4,770 package lines.
Keep the four-file core (521) and seven-file runtime mechanisms (823) separate
from that total. Removal must not sacrifice recovery or permission checks to hit
a line count. Dynamic dependency recovery and interactive plugin management stay deferred.

Rollback a removal PR by reverting it and restoring its compatible dependency
metadata; preserve session data. Do not automatically replay interrupted tools.
