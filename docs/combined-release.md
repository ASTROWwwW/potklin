# Combined development increment (0.3.0, not stable 1.0)

Implemented: developer-owned manifests, bounded read-only model missions, DAG executor with parallel independent tools and failed-dependency blocking, explicit provenance notes with lexical retrieval, AST source review and symbol inventory, local model adapter, Windows visible-window observation and explicit app launch. Scheduler policy is a pure function using supplied measured samples, not actual device control. Git inspection helper is experimental and is not exposed to autonomous missions; only use trusted local repositories. No automatic mod creation.

Not implemented: full desktop UI automation, unrestricted keyboard/mouse control, browser actions, GitHub mutations, robust OS sandbox, full recursive autonomous planning, semantic embeddings or automatic memory learning, advanced red-team operations, runtime compatibility fix, actual accelerator scheduling, overclocking or fine-tuning. Do not market this increment as a complete V1.0. Windows and real-model tests remain pending until reports are received.

Run unit tests plus scripts.expanded_probe (100 fixture DAGs), scripts.integration_probe and scripts.v7_probe with installed local model tag, optionally scripts.windows_probe with explicit launch. Test results must distinguish model assertions from independent oracles.
