"""Compact untrusted observation text without inventing summaries."""
def pack(observations,budget=12000):
    if not 1000<=budget<=32000:
        raise ValueError("invalid context budget")
    if not observations:
        return []
    limit=max(100,budget//len(observations))
    out=[]
    for o in observations:
        row={k:v for k,v in o.items() if k!="data"}
        text=o.get("data","")
        if text:
            row["data"]=text[:limit]
            row["truncated"]=bool(o.get("truncated")) or len(text)>limit
        out.append(row)
    return out
