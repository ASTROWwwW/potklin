"""Optional local vision-model evaluation on synthetic generated images."""
import argparse
import base64
import io
import json
import random
from PIL import Image,ImageDraw,ImageFont
from potklin.ollama import Ollama
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--cases",type=int,default=12)
    a=p.parse_args()
    if not 1<=a.cases<=100:p.error("invalid cases")
    rng=random.Random(74219);passed=0
    client=Ollama(a.model)
    font=ImageFont.truetype("arial.ttf",56)
    for i in range(a.cases):
        expected=str(rng.randrange(100000,999999))
        image=Image.new("RGB",(640,220),"white")
        ImageDraw.Draw(image).text((50,65),expected,font=font,fill="black")
        buf=io.BytesIO();image.save(buf,format="PNG")
        try:
            r=client.chat([{"role":"user","content":"Read the six-digit number in the image. Return only the digits.","images":[base64.b64encode(buf.getvalue()).decode("ascii")]}],tokens=64)
            answer=r["message"]["content"].strip()
            ok=answer==expected
            row={"case":i,"expected":expected,"answer":answer,"passed":ok}
        except Exception as e:
            row={"case":i,"expected":expected,"passed":False,"error":type(e).__name__}
        passed+=int(row["passed"])
        print(json.dumps(row),flush=True)
    print(json.dumps({"suite":"vision_model","total":a.cases,"passed":passed}))
    return int(passed!=a.cases)
if __name__=="__main__":raise SystemExit(main())
