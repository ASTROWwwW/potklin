"""End-to-end browser navigation on a disposable loopback HTTP fixture."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from potklin.browser_session import BrowserSession,Scope
from potklin.browser_agent import browse
from potklin.ollama import Ollama

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        pages={"/":"<h1>Home</h1><a href='/index'>Catalog</a>","/index":"<h1>Catalog</h1><a href='/report'>Final report</a>","/report":"<h1>Final report</h1><p>Reference PK830194</p>"}
        if self.path not in pages:
            self.send_error(404)
            return
        body=pages[self.path].encode()
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args):
        pass

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="")
    a=p.parse_args()
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    base="http://127.0.0.1:"+str(server.server_port)
    try:
        with BrowserSession(Scope.from_urls([base])) as session:
            if a.model:
                result=browse(session,Ollama(a.model),"Find the exact reference in the final report; follow links from home.",base+"/")
                passed=result["status"]=="model_finished_unverified" and "PK830194" in result.get("answer","") and base+"/report" in result["visited"]
            else:
                session.navigate(base+"/")
                session.click_link(0)
                result=session.click_link(0)
                passed="PK830194" in result["text"]
            print(json.dumps({"suite":"browser_agent","model":bool(a.model),"passed":passed,"result":result}))
            return int(not passed)
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
if __name__=="__main__":
    raise SystemExit(main())
