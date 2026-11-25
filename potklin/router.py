"""Fast deterministic dispatch for explicitly requested, known operations."""
import re

def route(text):
    # Exact grammar: never treat arbitrary embedded instructions as an action.
    request = text.strip().casefold()
    match = re.fullmatch(r"(?:lance|ouvre|open|launch) (discord|notepad|bloc-notes)[.!]?", request)
    if match:
        app = "notepad" if match[1] == "bloc-notes" else match[1]
        return {"name":"windows.launch","args":{"app":app},"mod":"windows"}
    return None
