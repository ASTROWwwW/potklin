"""Local embedding index; explicit notes only, no implicit collection."""
import json
import math
import sqlite3

def unit(vector):
    if not isinstance(vector,list) or not 1<=len(vector)<=8192 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in vector):
        raise ValueError("invalid embedding")
    norm=math.sqrt(sum(x*x for x in vector))
    if not norm or not math.isfinite(norm):
        raise ValueError("invalid norm")
    return [x/norm for x in vector]

class SemanticMemory:
    def __init__(self,path,embed,model):
        self.db=sqlite3.connect(path)
        self.embed,self.model=embed,model
        self.db.execute("CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, source TEXT, body TEXT, model TEXT, vector TEXT)")
        self.db.commit()
    def add(self,key,source,body):
        if not key or not source or not body or len(body)>16000:
            raise ValueError("invalid note")
        v=unit(self.embed(body))
        self.db.execute("INSERT OR REPLACE INTO vectors VALUES(?,?,?,?,?)",(key,source,body,self.model,json.dumps(v)))
        self.db.commit()
    def search(self,query,limit=5):
        if not 1<=limit<=20 or not query or len(query)>1000:
            raise ValueError("invalid query")
        q=unit(self.embed(query))
        rows=[]
        for key,source,body,raw in self.db.execute("SELECT id,source,body,vector FROM vectors WHERE model=? LIMIT 10000",(self.model,)):
            v=json.loads(raw)
            if len(v)==len(q):
                rows.append({"id":key,"source":source,"body":body,"score":sum(a*b for a,b in zip(q,v))})
        return sorted(rows,key=lambda r:(-r["score"],r["id"]))[:limit]
    def delete(self,key):
        self.db.execute("DELETE FROM vectors WHERE id=?",(key,))
        self.db.commit()
    def close(self):
        self.db.close()
