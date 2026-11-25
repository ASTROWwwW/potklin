"""Opt-in Windows Sandbox runtime test on dedicated disposable mapped folders."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from potklin.sandbox import smoke_config

CHECK=r"""
$ErrorActionPreference='Stop'
$read=[IO.File]::ReadAllText('C:\PotklinFixture\marker.txt')
$blocked=$false
try { [IO.File]::WriteAllText('C:\PotklinFixture\attempt.txt','fixture write'); } catch { $blocked=$true }
@{marker=$read;write_blocked=$blocked} | ConvertTo-Json -Compress | Set-Content -LiteralPath 'C:\PotklinResult\result.json' -Encoding UTF8
"""
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--directory",required=True)
    p.add_argument("--launch",action="store_true")
    a=p.parse_args()
    if not a.launch:
        p.error("explicit sandbox launch required")
    root=Path(a.directory).resolve()
    root.mkdir(parents=True,exist_ok=False)
    source=root/"source"
    output=root/"output"
    source.mkdir();output.mkdir()
    (source/"marker.txt").write_text("POTKLIN_SANDBOX_4821",encoding="utf8")
    (source/"check.ps1").write_text(CHECK,encoding="utf8")
    wsb=root/"smoke.wsb"
    wsb.write_text(smoke_config(source,output),encoding="utf8")
    exe=Path(os.environ["SystemRoot"])/"System32"/"WindowsSandbox.exe"
    if not exe.is_file():
        raise FileNotFoundError("Windows Sandbox feature not available")
    subprocess.Popen([str(exe),str(wsb)],shell=False)
    end=time.monotonic()+180
    target=output/"result.json"
    while time.monotonic()<end:
        if target.is_file():
            try:
                result=json.loads(target.read_text(encoding="utf-8-sig"))
                passed=result.get("marker")=="POTKLIN_SANDBOX_4821" and result.get("write_blocked") is True and not (source/"attempt.txt").exists()
                print(json.dumps({"suite":"sandbox_runtime","passed":passed,"result":result,"network_configuration":"disabled; not independently probed"}))
                return int(not passed)
            except (OSError,ValueError):
                pass
        time.sleep(1)
    print(json.dumps({"suite":"sandbox_runtime","passed":False,"error":"no result within 180 seconds"}))
    return 1
if __name__=="__main__":
    raise SystemExit(main())
