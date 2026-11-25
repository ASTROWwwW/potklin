"""Static developer-owned manifests; no dynamic imports or external code."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Manifest:
    name: str
    version: str
    tools: tuple[str, ...]

MANIFESTS = (
    Manifest("filesystem","1.1",("files.read","files.list","files.search")),
    Manifest("cyber","1.1",("cyber.audit","cyber.ast_review")),
    Manifest("documents","1.0",("documents.html",)),
    Manifest("coding","1.0",("coding.symbols",)),
    Manifest("windows","1.1",("windows.launch","windows.status")),
)

def validate(registry):
    declared = {name: m.name for m in MANIFESTS for name in m.tools}
    actual = registry.select({m.name for m in MANIFESTS})
    if set(actual) != set(declared) or any(actual[n].mod != declared[n] for n in declared):
        raise ValueError("registry and manifests disagree")
