"""Observe visible top-level windows by PID and executable basename, without titles."""
import ctypes
from ctypes import wintypes
import os
import sys
import time

APPS = {"discord":"discord.exe","notepad":"notepad.exe"}

def status(app):
    if app.lower() not in APPS:
        raise ValueError("unknown application")
    if sys.platform != "win32":
        raise OSError("Windows only")
    u=ctypes.WinDLL("user32",use_last_error=True)
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    u.EnumWindows.argtypes=[callback,wintypes.LPARAM]
    u.EnumWindows.restype=wintypes.BOOL
    u.IsWindowVisible.argtypes=[wintypes.HWND]
    u.IsWindowVisible.restype=wintypes.BOOL
    u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype=wintypes.DWORD
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.CloseHandle.restype=wintypes.BOOL
    matches=set()
    @callback
    def visit(hwnd,unused):
        if not u.IsWindowVisible(hwnd):
            return True
        pid=wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        h=k.OpenProcess(0x1000,False,pid.value)
        if h:
            try:
                size=wintypes.DWORD(32768)
                buf=ctypes.create_unicode_buffer(size.value)
                if k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(size)):
                    if os.path.basename(buf.value).lower()==APPS[app.lower()]:
                        matches.add(pid.value)
            finally:
                k.CloseHandle(h)
        return True
    if not u.EnumWindows(visit,0):
        raise OSError("EnumWindows failed")
    return {"app":app.lower(),"visible":bool(matches),"pids":sorted(matches)}

def wait_visible(app, seconds=20):
    end=time.monotonic()+seconds
    while True:
        result=status(app)
        if result["visible"] or time.monotonic()>=end:
            return result
        time.sleep(.25)
