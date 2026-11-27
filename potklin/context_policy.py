"""Compact untrusted observation text without inventing summaries."""
FLOOR = 200


def pack(observations, budget=12000):
    """Share the budget newest first: the model acts on what it has just read."""
    if not 1000 <= budget <= 128000:
        raise ValueError("invalid context budget")
    if not observations:
        return []
    floor = min(FLOOR, budget // len(observations))
    remaining = budget
    out = []
    for older, o in zip(range(len(observations) - 1, -1, -1), reversed(observations)):
        row = {k: v for k, v in o.items() if k != "data"}
        text = o.get("data", "")
        if text:
            row["data"] = text[:max(0, remaining - floor * older)]
            row["truncated"] = bool(o.get("truncated")) or len(row["data"]) < len(text)
            remaining -= len(row["data"])
        out.append(row)
    return out[::-1]
