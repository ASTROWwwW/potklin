"""Generate an explicit Windows Sandbox configuration for trusted test fixtures."""
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,tostring
def config(source):
    p=Path(source).resolve(strict=True)
    if not p.is_dir():
        raise ValueError("fixture directory required")
    root=Element("Configuration")
    for tag,val in (("Networking","Disable"),("vGPU","Disable"),("ClipboardRedirection","Disable"),("PrinterRedirection","Disable"),("AudioInput","Disable"),("VideoInput","Disable"),("ProtectedClient","Enable")):
        SubElement(root,tag).text=val
    folder=SubElement(SubElement(root,"MappedFolders"),"MappedFolder")
    SubElement(folder,"HostFolder").text=str(p)
    SubElement(folder,"SandboxFolder").text=r"C:\PotklinFixture"
    SubElement(folder,"ReadOnly").text="true"
    return tostring(root,encoding="unicode")

def smoke_config(source,output):
    from xml.etree.ElementTree import fromstring
    root=fromstring(config(source))
    p=Path(output).resolve(strict=True)
    if not p.is_dir() or p==Path(source).resolve() or p.is_relative_to(Path(source).resolve()) or Path(source).resolve().is_relative_to(p):
        raise ValueError("separate dedicated output directory required")
    folders=root.find("MappedFolders")
    folder=SubElement(folders,"MappedFolder")
    SubElement(folder,"HostFolder").text=str(p)
    SubElement(folder,"SandboxFolder").text=r"C:\PotklinResult"
    SubElement(folder,"ReadOnly").text="false"
    cmd=SubElement(root,"LogonCommand")
    SubElement(cmd,"Command").text=r'powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\PotklinFixture\check.ps1'
    return tostring(root,encoding="unicode")
