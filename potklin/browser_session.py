"""User-scoped browser navigation. Model output cannot expand the origin set."""
import http.client
import queue
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit
from dataclasses import dataclass

MAX_REDIRECTS=5
MAX_BODY=5_000_000
# The socket timeout applies to each read; a trickling response needs a limit on the whole transfer.
FETCH_DEADLINE=15
# Nothing listens here. Chromium sends every request it makes on its own to this proxy, so whatever
# route() does not see (workers, prefetch, preconnect) fails instead of reaching the network.
DEAD_PROXY={"server":"http://127.0.0.1:9","bypass":"<-loopback>"}
LAUNCH_ARGS=["--disable-background-networking","--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
FORWARDED={"accept","accept-language","user-agent","cookie","referer"}

class _NoFollow(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def fetch(url,method,headers):
    """One approved request under a wall-clock limit, whatever part of the response is slow."""
    outcome=queue.Queue(1)
    def work():
        try:
            outcome.put((True,_transfer(url,method,headers)))
        except Exception as error:
            outcome.put((False,error))
    # An abandoned transfer keeps its own socket timeouts and size limit, and dies with the process.
    threading.Thread(target=work,daemon=True).start()
    try:
        succeeded,value=outcome.get(timeout=FETCH_DEADLINE)
    except queue.Empty:
        raise ValueError("response too slow") from None
    if not succeeded:
        raise value
    return value

def _transfer(url,method,headers):
    """The request itself, without proxy or redirect, performed outside the browser."""
    kept={k:v for k,v in headers.items() if k.lower() in FORWARDED}
    kept["Accept-Encoding"]="identity"
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoFollow())
    deadline=time.monotonic()+FETCH_DEADLINE
    try:
        response=opener.open(urllib.request.Request(url,method=method,headers=kept),timeout=5)
    except urllib.error.HTTPError as error:
        response=error
    with response:
        chunks=[]
        size=0
        while chunk:=response.read1(65536):
            size+=len(chunk)
            if size>MAX_BODY:
                raise ValueError("response too large")
            if time.monotonic()>deadline:
                raise ValueError("response too slow")
            chunks.append(chunk)
        # read1 reports a connection closed early as a normal end, so compare with the announced length.
        if method!="HEAD" and getattr(response,"length",None):
            raise ValueError("response cut off")
        body=b"".join(chunks)
        answer={}
        for name,value in response.headers.items():
            if name.lower() not in {"content-length","transfer-encoding","connection","content-encoding"}:
                key=name.lower()
                answer[key]=answer[key]+"\n"+value if key=="set-cookie" and key in answer else value
        return response.status,answer,body

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
            self.browser=self.p.chromium.launch(headless=True,proxy=DEAD_PROXY,args=LAUNCH_ARGS)
            self.ctx=self.browser.new_context(accept_downloads=False,service_workers="block")
            self.redirect=None
            self.page=None
            self.ctx.route("**/*",self._route)
            # route() does not see WebSockets. A handler that never calls connect_to_server keeps
            # them off the network; closing the socket here deadlocks the sync API.
            self.ctx.route_web_socket("**/*",lambda socket:None)
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
    def _route(self,route):
        # Playwright does not call a route handler again for a redirect target, so the
        # browser must never follow one: fetch without redirects and re-check each hop.
        request=route.request
        if not self.scope.allows(request.url) or request.method not in {"GET","HEAD"}:
            route.abort()
            return
        try:
            status,headers,body=fetch(request.url,request.method,request.headers)
        except (OSError,ValueError,http.client.HTTPException):
            route.abort()
            return
        location=headers.get("location")
        if 300<=status<400 and location:
            if self.page and request.is_navigation_request() and request.frame==self.page.main_frame:
                self.redirect=urljoin(request.url,location)
            # "aborted" avoids an error page that would interrupt the next navigation.
            route.abort("aborted")
            return
        route.fulfill(status=status,headers=headers,body=body)
    def navigate(self,url):
        from playwright.sync_api import Error
        for _ in range(MAX_REDIRECTS+1):
            if not self.scope.allows(url):
                raise PermissionError("outside browser scope")
            self.redirect=None
            try:
                self.page.goto(url,wait_until="domcontentloaded",timeout=10000)
            except Error:
                if self.redirect is None:
                    raise
                url=self.redirect
                continue
            return self.observe()
        raise PermissionError("too many redirects")
    def observe(self):
        if not self.scope.allows(self.page.url):
            raise PermissionError("outside browser scope")
        links=[]
        for el in self.page.locator("a[href]").all()[:100]:
            href=el.get_attribute("href") or ""
            url=urljoin(self.page.url,href)
            if self.scope.allows(url):
                links.append({"url":url,"text":el.inner_text()[:200]})
        return {"url":self.page.url,"title":self.page.title()[:200],"text":self.page.locator("body").inner_text()[:12000],"links":links}
    def click_link(self,index):
        data=self.observe()
        if not isinstance(index,int) or not 0<=index<len(data["links"]):
            raise ValueError("invalid link index")
        return self.navigate(data["links"][index]["url"])

    def fill_field(self,element_id,value,confirmed=False):
        """Explicit filling only, not submission or credential collection."""
        if not confirmed:raise PermissionError("explicit confirmation required")
        if not element_id or len(element_id)>80 or not element_id.replace("-","").replace("_","").isalnum() or len(value)>2000:
            raise ValueError("invalid field")
        if not self.scope.allows(self.page.url):raise PermissionError("outside scope")
        el=self.page.locator("#"+element_id)
        if el.count()!=1:raise ValueError("field not unique")
        if (el.get_attribute("type") or "").lower() in {"password","hidden","file"}:
            raise PermissionError("restricted field")
        el.fill(value)
        return {"filled":element_id,"verified":el.input_value()==value}
