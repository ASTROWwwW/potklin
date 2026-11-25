"""Reuse the V5 cached OCR model. Synthetic text fixtures only."""
import argparse
import json
import os
from pathlib import Path
from statistics import median
import time

def main():
    import numpy as np
    import openvino as ov
    from PIL import Image,ImageDraw,ImageFont
    p=argparse.ArgumentParser()
    p.add_argument("--xml",required=True)
    a=p.parse_args()
    model=Path(a.xml).resolve(strict=True)
    core=ov.Core()
    m=core.read_model(str(model))
    font=ImageFont.truetype(str(Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"/"arial.ttf"),40)
    samples=[]
    for text in ("potklin","4821","windows","security","discord","network","12345","memory"):
        im=Image.new("L",(320,100),255)
        d=ImageDraw.Draw(im)
        box=d.textbbox((0,0),text,font=font)
        d.text((5-box[0],5-box[1]),text,fill=0,font=font)
        im=im.crop((0,0,box[2]-box[0]+10,box[3]-box[1]+10)).resize((120,32))
        samples.append((text,np.array(im,dtype=np.float32)[None,:,:,None]))
    alphabet="0123456789abcdefghijklmnopqrstuvwxyz#"
    ok=False
    for device in core.available_devices:
        try:
            compiled=core.compile_model(m,device)
            request=compiled.create_infer_request()
            def recognize(x):
                y=request.infer({0:x})[compiled.output(0)]
                ids=np.argmax(np.asarray(y).reshape(-1,37),axis=1)
                return "".join(alphabet[int(v)] for i,v in enumerate(ids) if v!=36 and (i==0 or v!=ids[i-1]))
            answers=[]
            times=[]
            for expected,x in samples:
                t=time.perf_counter()
                answer=recognize(x)
                times.append((time.perf_counter()-t)*1000)
                answers.append({"expected":expected,"answer":answer})
            passed=sum(x["answer"]==x["expected"] for x in answers)
            ok=ok or (device=="CPU" and passed==len(samples))
            print(json.dumps({"device":device,"passed":passed,"total":len(samples),"median_ms":median(times),"answers":answers}),flush=True)
        except Exception as e:
            print(json.dumps({"device":device,"error":str(e)}),flush=True)
    return int(not ok)
if __name__=="__main__":
    raise SystemExit(main())
