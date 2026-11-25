"""User-scoped browser navigation. Model output cannot expand the origin set."""
from urllib.parse import urlsplit
from dataclasses import dataclass

def origin(url):
    if not isinstance(url,str) or "\\" in url or any(ord(x)<32 or ord(x)==127 for x in url):
        raise ValueError("invalid URL")
    u=urlsplit(url)
    if u.scheme not in {"http","https"} or not u.hostname or u.username or u.password:
        raise ValueError("HTTP(S) URL without credentials required")
    if u.scheme=="http" and u.hostname not in {"localhost","127.0.0.1","::1"}:
        raise ValueError("plain HTTP restricted to loopback")
    return (u.scheme,u.hostname.lower(),u.port or (443 if u.scheme=="https" else 80))

@dataclass(frozen=True)
class Scope:
    origins: frozenset
    @classmethod
    def from_urls(cls,urls):
        return cls(frozenset(origin(u) for u in urls))
    def allows(self,url):
        try:
            return origin(url) in self.origins
        except (ValueError,TypeError):
            return False

class BrowserSession:
    """Ephemeral browser; no credentials, persistent profile, downloads or external origins.
    Scope is not a network sandbox. Use only approved trusted origins.
    """
    def __init__(self,scope):
        self.scope=scope
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.p=sync_playwright().start()
        try:
            self.browser=self.p.chromium.launch(headless=True,args=["--disable-background-networking"])
            self.ctx=self.browser.new_context(accept_downloads=False,service_workers="block")
            self.ctx.route("**/*",lambda route:route.continue_() if self.scope.allows(route.request.url) and route.request.method in {"GET","HEAD"} else route.abort())
            self.page=self.ctx.new_page()
            self.page.set_default_timeout(5000)
            return self
        except Exception:
            self.p.stop()
            raise
    def __exit__(self,*exc):
        try:
            self.browser.close()
        finally:
            self.p.stop()
    def navigate(self,url):
        if not self.scope.allows(url):
            raise PermissionError("outside browser scope")
        self.page.goto(url,wait_until="domcontentloaded",timeout=10000)
        if not self.scope.allows(self.page.url):
            raise PermissionError("redirect outside scope")
        return self.observe()
    def observe(self):
        if not self.scope.allows(self.page.url):
            raise PermissionError("outside browser scope")
        links=[]
        for el in self.page.locator("a[href]").all()[:100]:
            href=el.get_attribute("href") or ""
            from urllib.parse import urljoin
            url=urljoin(self.page.url,href)
            if self.scope.allows(url):
                links.append({"url":url,"text":el.inner_text()[:200]})
        return {"url":self.page.url,"title":self.page.title()[:200],"text":self.page.locator("body").inner_text()[:12000],"links":links}
    def click_link(self,index):
        data=self.observe()
        if not isinstance(index,int) or not 0<=index<len(data["links"]):
            raise ValueError("invalid link index")
        return self.navigate(data["links"][index]["url"])
