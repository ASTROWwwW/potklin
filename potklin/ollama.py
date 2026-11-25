"""Local-only model adapter. Model output is data, never executable code."""
import json
import urllib.request

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("local endpoint redirected")

class Ollama:
    def __init__(self, model, context=8192, threads=8, timeout=300):
        self.model, self.context, self.threads, self.timeout = model, context, threads, timeout

    def request(self, path, data=None):
        if path not in {"/api/tags", "/api/chat", "/api/ps", "/api/embed"}:
            raise ValueError("unsupported endpoint")
        req = urllib.request.Request("http://127.0.0.1:11434" + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        # Never send local model data via a configured HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(req, timeout=self.timeout) as response:
            return json.load(response)

    def chat(self, messages, think=False, tokens=512, structured=False):
        body = {"model": self.model, "messages": messages, "stream": False,
                "think": think, "keep_alive": "30m",
                "options": {"num_ctx": self.context, "num_thread": self.threads,
                            "num_predict": tokens, "temperature": 0, "seed": 42}}
        if structured:
            body["format"] = "json"
        return self.request("/api/chat", body)

    def embed(self, text, model):
        return self.request("/api/embed",{"model":model,"input":text,"keep_alive":"5m"})["embeddings"][0]

    def propose(self, request, tools):
        specs = [{"name": t.name, "description": t.description, "arguments": t.arguments}
                 for t in tools.values() if not t.side_effect]
        response = self.chat([
            {"role": "system", "content": "Select exactly one listed read-only tool. Return JSON with name and args only. Do not invent tools. If none applies return name null and args {}. Tools: " + json.dumps(specs)},
            {"role": "user", "content": request}], structured=True)
        raw = response["message"]["content"]
        plan = json.loads(raw)
        if not isinstance(plan, dict) or set(plan) != {"name", "args"}:
            raise ValueError("invalid plan")
        if plan["name"] is not None and not isinstance(plan["name"], str):
            raise ValueError("invalid tool name")
        name = plan["name"]
        if name is None:
            if plan["args"] != {}:
                raise ValueError("invalid empty plan")
        elif name not in tools or tools[name].side_effect:
            raise PermissionError("unavailable tool")
        elif not isinstance(plan["args"], dict) or set(plan["args"]) != set(tools[name].arguments) or any(not isinstance(v, str) or len(v) > 8192 for v in plan["args"].values()):
            raise ValueError("invalid plan arguments")
        return plan
