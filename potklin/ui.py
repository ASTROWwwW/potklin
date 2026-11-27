"""Explicit local GUI for read-only missions. No automatic desktop actions."""
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk
from .core import Journal
from .mods import build_registry
from .mission import MissionRunner
from .ollama import Ollama

def launch(workspace,model,journal):
    root=tk.Tk()
    root.title("Potklin")
    root.geometry("850x650")
    request=ttk.Entry(root)
    request.pack(fill="x",padx=12,pady=12)
    output=tk.Text(root,wrap="word")
    output.pack(fill="both",expand=True,padx=12,pady=8)
    events=queue.Queue()
    def run():
        text=request.get().strip()
        if not text:
            return
        button.configure(state="disabled")
        def worker():
            j=None
            try:
                j=Journal(journal)
                # Thinking alone may use 8192 output tokens, so the default 8192 window is too small.
                result=MissionRunner(build_registry(workspace),j,Ollama(model,context=24576)).run(text,{"filesystem","coding","cyber","documents"},10,True)
                events.put(json.dumps(result,ensure_ascii=False,indent=2))
            except Exception as e:
                events.put(type(e).__name__+": "+str(e))
            finally:
                if j:
                    j.close()
        threading.Thread(target=worker,daemon=True).start()
    button=ttk.Button(root,text="Run read-only mission",command=run)
    button.pack(pady=8)
    def poll():
        try:
            value=events.get_nowait()
            output.delete("1.0","end")
            output.insert("end",value)
            button.configure(state="normal")
        except queue.Empty:
            pass
        root.after(100,poll)
    root.after(100,poll)
    root.mainloop()
