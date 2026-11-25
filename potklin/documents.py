"""Bounded local HTML analysis. No network or scripts."""
from html.parser import HTMLParser
class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.parts=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style"}:
            self.hidden+=1
        if tag=="a" and not self.hidden:
            href=dict(attrs).get("href","")
            if href and len(self.links)<100:
                self.links.append(href[:1000])
    def handle_endtag(self,tag):
        if tag in {"script","style"}:
            self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden and data.strip() and len(self.parts)<2000:
            self.parts.append(data.strip())
def inspect(workspace,path):
    if not path.lower().endswith((".html",".htm")):
        raise ValueError("HTML file required")
    parser=Page()
    parser.feed(workspace.read(path)["text"])
    parser.close()
    text=" ".join(parser.parts)
    return {"path":path,"text":text[:16000],"links":parser.links,"truncated":len(text)>16000}
