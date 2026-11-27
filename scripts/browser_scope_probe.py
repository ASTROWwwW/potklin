"""Prove that nothing reaches an out-of-scope origin: redirects, subresources and WebSockets."""
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


def inside_handler(outside, outside_port):
    class Inside(BaseHTTPRequestHandler):
        def redirect(self, location):
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def page(self, body):
            raw = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == "/leak":
                self.redirect(outside + "/redirected")
            elif self.path == "/hop":
                self.redirect("/hop2")
            elif self.path == "/hop2":
                self.redirect(outside + "/second-hop")
            elif self.path == "/moved":
                self.redirect("/target")
            elif self.path == "/loop":
                self.redirect("/loop")
            elif self.path == "/target":
                self.page("<h1>Moved here</h1><a href='next'>Next</a>")
            elif self.path == "/image-redirect":
                self.redirect(outside + "/image")
            elif self.path == "/active":
                self.page("<h1>Active</h1><img src='/image-redirect'><img src='" + outside + "/direct-image'>"
                          "<script>new WebSocket('ws://127.0.0.1:" + str(outside_port) + "/socket');"
                          "fetch('" + outside + "/fetch').catch(()=>{});</script>")
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    return Inside


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    outside_server = serve(Outside)
    outside = f"http://127.0.0.1:{outside_server.server_port}"
    inside_server = serve(inside_handler(outside, outside_server.server_port))
    inside = f"http://127.0.0.1:{inside_server.server_port}"
    outcomes = {}
    try:
        with BrowserSession(Scope.from_urls([inside])) as session:
            for path in ("/leak", "/hop", "/loop", "/moved", "/active"):
                try:
                    observed = session.navigate(inside + path)
                    outcomes[path] = {"url": observed["url"].removeprefix(inside), "title_ok": True}
                except Exception as error:
                    outcomes[path] = {"error": type(error).__name__}
            session.page.wait_for_timeout(1000)
        time.sleep(0.2)
    finally:
        for server in (inside_server, outside_server):
            server.shutdown()
            server.server_close()
    blocked = all("error" in outcomes[p] for p in ("/leak", "/hop", "/loop"))
    legitimate = outcomes["/moved"].get("url") == "/target" and outcomes["/active"].get("url") == "/active"
    passed = not reached and blocked and legitimate
    print(json.dumps({"suite": "browser_scope", "passed": passed, "reached_outside": sorted(set(reached)), "outcomes": outcomes}))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
