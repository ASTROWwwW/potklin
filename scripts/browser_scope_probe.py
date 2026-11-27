"""Prove that nothing reaches an out-of-scope origin, not even a bare TCP connection.

Covers redirects, subresources, WebSockets, dedicated and shared workers, prefetch,
preconnect and speculation rules.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from potklin.browser_session import BrowserSession, Scope

reached = []


class Outside(BaseHTTPRequestHandler):
    def do_GET(self):
        reached.append(self.path)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"outside")

    def log_message(self, *args):
        pass


class CountingServer(ThreadingHTTPServer):
    def process_request(self, request, client_address):
        reached.append("<connection>")
        super().process_request(request, client_address)


def inside_handler(outside, outside_port):
    socket_url = "ws://127.0.0.1:" + str(outside_port)
    worker = (f"new WebSocket('{socket_url}/worker-socket');"
              f"fetch('{outside}/worker-fetch').catch(()=>{{}});")
    shared = (f"new WebSocket('{socket_url}/shared-socket');"
              f"fetch('{outside}/shared-fetch').catch(()=>{{}});")
    pages = {
        "/target": "<h1>Moved here</h1><a href='next'>Next</a>",
        "/active": ("<h1>Active</h1><img src='/image-redirect'><img src='" + outside + "/direct-image'>"
                    "<script>new WebSocket('" + socket_url + "/socket');"
                    "fetch('" + outside + "/fetch').catch(()=>{});</script>"),
        "/workers": ("<h1>Workers</h1><script>new Worker('/worker.js'); new SharedWorker('/shared.js');"
                     "document.body.append('script-ran');</script>"),
        "/hints": ("<link rel='prefetch' href='" + outside + "/prefetch'><link rel='preconnect' href='" + outside + "'>"
                   "<link rel='prerender' href='" + outside + "/prerender'>"
                   "<script type='speculationrules'>" + json.dumps({
                       "prefetch": [{"source": "list", "urls": [outside + "/speculation-prefetch"]}],
                       "prerender": [{"source": "list", "urls": [outside + "/speculation-prerender"]}]}) +
                   "</script><h1>Hints</h1>"),
    }
    scripts = {"/worker.js": worker, "/shared.js": shared}
    redirects = {"/leak": outside + "/redirected", "/hop": "/hop2", "/hop2": outside + "/second-hop",
                 "/moved": "/target", "/loop": "/loop", "/image-redirect": outside + "/image"}

    class Inside(BaseHTTPRequestHandler):
        def reply(self, body, content_type):
            raw = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path in redirects:
                self.send_response(302)
                self.send_header("Location", redirects[self.path])
                self.end_headers()
            elif self.path in pages:
                self.reply(pages[self.path], "text/html; charset=utf-8")
            elif self.path in scripts:
                self.reply(scripts[self.path], "text/javascript")
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    return Inside


def serve(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    outside_server = serve(CountingServer(("127.0.0.1", 0), Outside))
    outside = f"http://127.0.0.1:{outside_server.server_port}"
    inside_server = serve(ThreadingHTTPServer(("127.0.0.1", 0), inside_handler(outside, outside_server.server_port)))
    inside = f"http://127.0.0.1:{inside_server.server_port}"
    outcomes = {}
    try:
        with BrowserSession(Scope.from_urls([inside])) as session:
            for path in ("/leak", "/hop", "/loop", "/moved", "/active", "/workers", "/hints"):
                try:
                    observed = session.navigate(inside + path)
                    session.page.wait_for_timeout(1500)
                    outcomes[path] = {"url": observed["url"].removeprefix(inside), "text": session.observe()["text"][:60]}
                except Exception as error:
                    outcomes[path] = {"error": type(error).__name__}
        time.sleep(0.2)
    finally:
        for server in (inside_server, outside_server):
            server.shutdown()
            server.server_close()
    blocked = all("error" in outcomes[p] for p in ("/leak", "/hop", "/loop"))
    # Positive controls: allowed redirects are followed, and in-scope scripts still run.
    legitimate = (outcomes["/moved"].get("url") == "/target" and outcomes["/active"].get("url") == "/active"
                  and "script-ran" in outcomes["/workers"].get("text", ""))
    passed = not reached and blocked and legitimate
    print(json.dumps({"suite": "browser_scope", "passed": passed, "reached_outside": sorted(set(reached)), "outcomes": outcomes}))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
