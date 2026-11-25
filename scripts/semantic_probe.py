import argparse
import json
import tempfile
from pathlib import Path
from potklin.semantic import SemanticMemory
from potklin.ollama import Ollama

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    a=p.parse_args()
    client=Ollama(a.model)
    with tempfile.TemporaryDirectory() as d:
        m=SemanticMemory(Path(d)/"vectors.db",lambda s:client.embed(s,a.model),a.model)
        try:
            for key,body in [("gpu","A graphics processor accelerates neural network inference."),("food","Pasta is cooked in boiling water."),("music","A piano has black and white keys.")]:
                m.add(key,"synthetic fixture",body)
            rows=m.search("hardware for running an AI model")
            passed=bool(rows) and rows[0]["id"]=="gpu"
            print(json.dumps({"suite":"semantic_memory","passed":passed,"ranked":rows}))
            return int(not passed)
        finally:
            m.close()
if __name__=="__main__":
    raise SystemExit(main())
