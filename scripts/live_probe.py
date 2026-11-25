"""Local inference smoke/latency probe, no external actions."""
import json
import sys
import time
from potklin.ollama import Ollama
from statistics import median

client = Ollama(sys.argv[1])
rows = []
for think in (False, True):
    for i in range(3):
        start = time.perf_counter()
        try:
            r = client.chat([{"role":"user","content":"Return only the integer: 17 * 23 + 19"}], think=think, tokens=4096 if think else 256)
            elapsed = time.perf_counter()-start
            rows.append({"think":think,"run":i,"seconds":elapsed,"answer":r["message"]["content"],
                         "done_reason":r.get("done_reason"),"eval_count":r.get("eval_count"),
                         "decode_tps":r.get("eval_count",0)*1e9/max(1,r.get("eval_duration",0)),
                         "exact":r["message"]["content"].strip()=="410"})
        except Exception as e:
            rows.append({"think":think,"run":i,"error":str(e)})
        print(json.dumps(rows[-1]), flush=True)
if any("error" in r for r in rows):
    sys.exit(1)
