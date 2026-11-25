"""Explicit local fine-tuning pipeline; requires reviewed text dataset and local HF weights.
Never downloads a model, never executes model repository code.
"""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model-dir",required=True)
    p.add_argument("--dataset",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--steps",type=int,default=20)
    p.add_argument("--device",choices=["cpu","cuda"],default="cuda")
    p.add_argument("--confirmed",action="store_true")
    a=p.parse_args()
    if not a.confirmed or not 1<=a.steps<=1000:
        p.error("explicit reviewed-dataset confirmation and bounded steps required")
    model_dir=Path(a.model_dir).resolve(strict=True)
    if not model_dir.is_dir() or not list(model_dir.glob("*.safetensors")):
        p.error("local safetensors checkpoint required")
    output=Path(a.output)
    if output.exists():
        p.error("output already exists")
    samples=[]
    with open(a.dataset,encoding="utf-8") as f:
        for line in f:
            if len(samples)>=10000:
                break
            row=json.loads(line)
            if row.get("reviewed") is not True or not isinstance(row.get("text"),str) or not 1<=len(row["text"])<=16000:
                p.error("each row requires reviewed:true and bounded text")
            samples.append(row["text"])
    if len(samples)<2:
        p.error("at least two reviewed samples required")
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import LoraConfig,get_peft_model
    torch.manual_seed(42)
    tok=AutoTokenizer.from_pretrained(str(model_dir),local_files_only=True,trust_remote_code=False)
    base=AutoModelForCausalLM.from_pretrained(str(model_dir),local_files_only=True,trust_remote_code=False,use_safetensors=True)
    model=get_peft_model(base,LoraConfig(r=8,lora_alpha=16,target_modules="all-linear",task_type="CAUSAL_LM")).to(a.device)
    params=[v for v in model.parameters() if v.requires_grad]
    opt=torch.optim.AdamW(params,lr=1e-4)
    model.train()
    for i in range(a.steps):
        tokens=tok(samples[i%len(samples)],return_tensors="pt",truncation=True,max_length=512)
        x=tokens["input_ids"].to(a.device)
        if x.shape[1]<2:
            raise ValueError("sample too short")
        opt.zero_grad()
        loss=model(input_ids=x,labels=x).loss
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params,1.)
        opt.step()
        print(json.dumps({"step":i,"loss":float(loss.detach().cpu())}),flush=True)
    model.save_pretrained(str(output),safe_serialization=True)
    tok.save_pretrained(str(output))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
