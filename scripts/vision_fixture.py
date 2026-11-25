"""Synthetic screenshot and optional OCR, no personal desktop capture."""
import argparse
import json
import tempfile
from pathlib import Path

def main():
    from PIL import Image,ImageDraw,ImageFont
    p=argparse.ArgumentParser()
    p.add_argument("--ocr",action="store_true")
    a=p.parse_args()
    im=Image.new("RGB",(640,240),"white")
    draw=ImageDraw.Draw(im)
    try:
        font=ImageFont.truetype("arial.ttf",48)
    except OSError:
        font=ImageFont.load_default()
    draw.text((40,80),"POTKLIN 4821",fill="black",font=font)
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"fixture.png"
        im.save(path)
        with Image.open(path) as loaded:
            ok=loaded.size==(640,240) and loaded.getextrema()!=((255,255),(255,255),(255,255))
        result={"suite":"vision_fixture","image_verified":ok,"ocr_executed":False}
        if a.ocr:
            import pytesseract
            recognized=pytesseract.image_to_string(im,config="--psm 7").strip()
            result.update(ocr_executed=True,text=recognized,ocr_verified="4821" in recognized)
            ok=ok and result["ocr_verified"]
        print(json.dumps(result))
        return int(not ok)
if __name__=="__main__":
    raise SystemExit(main())
