"""UI Automation observation of an explicitly selected application.
Optional pywinauto dependency. No global input hooks or password collection.
"""
from .windows import status

def tree(app):
    from pywinauto import Desktop
    observed=status(app)
    if not observed["visible"]:
        return {"app":app,"windows":[]}
    result=[]
    desktop=Desktop(backend="uia")
    for window in desktop.windows():
        if window.element_info.process_id not in observed["pids"]:
            continue
        nodes=[]
        for child in window.descendants(depth=4)[:200]:
            info=child.element_info
            kind=info.control_type
            # Never read editable values; only limited structural metadata.
            nodes.append({"type":kind,"automation_id":str(info.automation_id or "")[:120]})
        result.append({"controls":nodes})
        if len(result)>=5:
            break
    return {"app":app,"windows":result}
