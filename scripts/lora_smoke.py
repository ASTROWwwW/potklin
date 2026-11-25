"""Offline LoRA training smoke on an initialized tiny model (no downloads).
Not a fine-tune of the primary model. Optional ML dependencies required.
"""
import argparse
import json
import tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    a=p.parse_args()
    import torch
    from transformers import GPT2Config,GPT2LMHeadModel
    from peft import LoraConfig,get_peft_model
    torch.manual_seed(42)
    model=GPT2LMHeadModel(GPT2Config(vocab_size=64,n_positions=32,n_embd=32,n_layer=2,n_head=2,bos_token_id=1,eos_token_id=2))
    model=get_peft_model(model,LoraConfig(r=4,lora_alpha=8,target_modules=["c_attn"],task_type="CAUSAL_LM",fan_in_fan_out=True)).to(a.device)
    trainable=[p for p in model.parameters() if p.requires_grad]
    before=[p.detach().clone() for p in trainable]
    x=torch.tensor([[1,4,5,6,7,2],[1,4,5,6,7,2]],device=a.device)
    opt=torch.optim.AdamW(trainable,lr=.01)
    losses=[]
    model.train()
    for _ in range(12):
        opt.zero_grad()
        loss=model(input_ids=x,labels=x).loss
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().cpu()))
    changed=any(not torch.equal(b,p.detach()) for b,p in zip(before,trainable))
    with tempfile.TemporaryDirectory() as d:
        model.save_pretrained(d,safe_serialization=True)
        saved=(Path(d)/"adapter_model.safetensors").is_file()
    ok=changed and saved and all(torch.isfinite(torch.tensor(losses)))
    print(json.dumps({"suite":"lora_smoke","device":a.device,"passed":bool(ok),"losses":losses,"trainable":sum(p.numel() for p in trainable),"adapter_saved":saved}))
    return int(not ok)
if __name__=="__main__":
    raise SystemExit(main())
