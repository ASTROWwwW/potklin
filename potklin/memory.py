"""Explicit local notes with provenance and bounded lexical retrieval."""
import sqlite3
import time
import hashlib
import re

class Memory:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, source TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL)")
        self.db.commit()
    def add(self,source,body):
        if not isinstance(source,str) or not isinstance(body,str) or not source.strip() or not body.strip() or len(source)>512 or len(body)>16000:
            raise ValueError("invalid note")
        key=hashlib.sha256((source+"\0"+body).encode()).hexdigest()
        self.db.execute("INSERT OR IGNORE INTO notes VALUES (?,?,?,?)",(key,source,body,time.time()))
        self.db.commit()
        return key
    def search(self,query,limit=5):
        if not isinstance(query,str) or len(query)>1000 or not 1<=limit<=20:
            raise ValueError("invalid query")
        terms=set(re.findall(r"\w+",query.casefold()))
        rows=[]
        for key,source,body,created in self.db.execute("SELECT id,source,body,created FROM notes ORDER BY created DESC LIMIT 5000"):
            score=len(terms & set(re.findall(r"\w+",(source+" "+body).casefold())))
            if score:
                rows.append({"id":key,"source":source,"body":body,"score":score,"created":created})
        return sorted(rows,key=lambda x:(-x["score"],-x["created"],x["id"]))[:limit]
    def delete(self,key):
        self.db.execute("DELETE FROM notes WHERE id=?",(key,))
        self.db.commit()
    def close(self):
        self.db.close()
