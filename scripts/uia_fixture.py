"""Real UIA click and text verification on a disposable Windows Forms fixture.
Uses UI Automation rather than global keyboard hooks or arbitrary desktop actions.
"""
import json
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path

FORM=r"""
Add-Type -AssemblyName System.Windows.Forms
$f=New-Object System.Windows.Forms.Form
$f.Text='Potklin UIA fixture'
$f.Width=420
$f.Height=220
$t=New-Object System.Windows.Forms.TextBox
$t.Name='fixtureInput'
$t.AccessibleName='fixtureInput'
$t.Top=20
$t.Left=20
$t.Width=320
$b=New-Object System.Windows.Forms.Button
$b.Text='Verify'
$b.AccessibleName='fixtureButton'
$b.Top=60
$b.Left=20
$l=New-Object System.Windows.Forms.Label
$l.Text='Pending'
$l.AccessibleName='fixtureOutput'
$l.Top=100
$l.Left=20
$l.Width=320
$b.Add_Click({ $l.Text='Verified '+$t.Text })
$f.Controls.AddRange(@($t,$b,$l))
[void]$f.ShowDialog()
"""
def main():
    if sys.platform!="win32":
        raise OSError("Windows only")
    from pywinauto import Application
    with tempfile.TemporaryDirectory() as d:
        script=Path(d)/"form.ps1"
        script.write_text(FORM,encoding="utf-8")
        ps=Path(os.environ["SystemRoot"])/"System32"/"WindowsPowerShell"/"v1.0"/"powershell.exe"
        process=subprocess.Popen([str(ps),"-NoProfile","-STA","-ExecutionPolicy","Bypass","-File",str(script)])
        try:
            app=Application(backend="uia").connect(process=process.pid,timeout=20)
            win=app.window(title="Potklin UIA fixture")
            win.wait("visible ready",timeout=20)
            edit=win.child_window(control_type="Edit")
            edit.set_edit_text("4821")
            win.child_window(title="Verify",control_type="Button").invoke()
            deadline=time.monotonic()+5
            passed=False
            while time.monotonic()<deadline:
                if any(x.window_text()=="Verified 4821" for x in win.descendants(control_type="Text")):
                    passed=True
                    break
                time.sleep(.1)
            print(json.dumps({"suite":"uia_fixture","passed":passed,"method":"UIA set text and invoke"}))
            return int(not passed)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
if __name__=="__main__":
    raise SystemExit(main())
