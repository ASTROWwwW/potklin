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

def capture(app,output,confirmed=False):
    """Explicit local capture of a selected visible window; may include overlapping UI."""
    if not confirmed:
        raise PermissionError("explicit screenshot confirmation required")
    from pathlib import Path
    from pywinauto import Desktop
    pids=status(app)["pids"]
    windows=[w for w in Desktop(backend="uia").windows() if w.element_info.process_id in pids and w.is_visible()]
    if len(windows)!=1:
        raise ValueError("exactly one matching visible window required")
    path=Path(output)
    if path.suffix.lower()!=".png":
        raise ValueError("PNG path required")
    im=windows[0].capture_as_image()
    if im is None or im.width*im.height>16000000:
        raise ValueError("invalid capture")
    with path.open("xb") as handle:
        im.save(handle,format="PNG")
    return {"path":str(path),"width":im.width,"height":im.height,"local_only":True}
