"""Explicit scoped UIA interactions; never autonomously sends global input."""
from .windows import status

def control(app,automation_id,kind,action,text="",confirmed=False):
    if not confirmed:
        raise PermissionError("explicit confirmation required")
    if not automation_id or len(automation_id)>120 or kind not in {"Button","Edit","CheckBox"}:
        raise ValueError("invalid control selector")
    if action not in {"invoke","set_text","click","press"} or (action=="set_text" and kind!="Edit"):
        raise ValueError("unsupported control action")
    if len(text)>2000 or "\x00" in text:
        raise ValueError("invalid text")
    from pywinauto import Desktop
    pids=status(app)["pids"]
    matches=[]
    for win in Desktop(backend="uia").windows():
        if win.element_info.process_id in pids:
            matches.extend(c for c in win.descendants(depth=5) if c.element_info.automation_id==automation_id and c.element_info.control_type==kind)
    if len(matches)!=1:
        raise ValueError("control must be unique")
    target=matches[0]
    if target.element_info.process_id not in status(app)["pids"] or not target.is_enabled():
        raise PermissionError("target changed or disabled")
    # No password fields, clipboard or global SendKeys.
    if action=="set_text":
        if target.element_info.element.CurrentIsPassword:
            raise PermissionError("password control")
        target.set_edit_text(text)
        return {"action":action,"verified":target.get_value()==text}
    if action in {"click","press"}:
        import ctypes
        from ctypes import wintypes
        u=ctypes.WinDLL("user32",use_last_error=True)
        u.GetForegroundWindow.restype=wintypes.HWND
        u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        if action=="press" and text not in {"ENTER","ESC","TAB","SPACE"}:
            raise ValueError("unsupported key")
        if kind=="Edit" and target.element_info.element.CurrentIsPassword:
            raise PermissionError("password control")
        target.set_focus()
        pid=wintypes.DWORD()
        u.GetWindowThreadProcessId(u.GetForegroundWindow(),ctypes.byref(pid))
        if pid.value!=target.element_info.process_id or pid.value not in status(app)["pids"]:
            raise PermissionError("foreground target mismatch")
        if action=="click":
            target.click_input()
        else:
            target.type_keys("{"+text+"}",set_foreground=False)
        return {"action":action,"verified":False,"status":"input requested; outcome requires observation"}
    target.invoke()
    return {"action":action,"verified":False,"status":"invoked; outcome requires observation"}
