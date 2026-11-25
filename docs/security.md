# Security and reliability

Treat model output, web pages, repository files, tool output and skills as untrusted data. A separate policy engine authorizes every action before execution, including deterministic workflows. Use typed arguments, workspace confinement, least privilege and network/process restrictions. Never expose credentials to the model or commit raw logs with secrets.

Require explicit authorization for destructive, externally visible or irreversible actions outside an approved mission policy. Git push verification checks the intended repository, ref and remote SHA; never retry an unknown outcome blindly. Use isolated worktrees for competing candidate patches. Reconcile interrupted side effects before replay. Maintain audit logs and redact sensitive fields.

Test path traversal, symlinks, shell argument injection, malicious skills, prompt injection, duplicate execution, process timeouts, checkpoint corruption, stale proof, invalid structured output, resource exhaustion and recovery after interruption.

Security boundaries are enforced by software, not model refusal behavior. Keep training and learned skills offline/reviewed until validated. Do not claim that tests prove absence of vulnerabilities.
