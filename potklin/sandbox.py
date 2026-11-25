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
