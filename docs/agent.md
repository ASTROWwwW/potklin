# Using the agent

The agent works on one workspace with a local Ollama model. You decide what it may do and what counts as success.

## Install

```sh
python -m pip install .        # Python 3.12 or newer, no runtime dependency
potklin doctor                 # is Ollama reachable and is the model installed?
```

`--model` selects the model. Global options (`--workspace`, `--model`, `--context`, `--journal`) go before the subcommand.

## Run a mission

A read-only question needs nothing else:

```sh
potklin --workspace path/to/project mission "Where is the retry delay computed?"
```

To let it fix something and prove it, declare the commands it may run in a JSON file kept outside the workspace:

```json
{ "test": ["python", "-m", "unittest", "discover", "-s", "tests"] }
```

```sh
potklin --workspace path/to/project mission "Fix the failing test" \
  --allow-write --commands ~/commands.json --allow-exec \
  --check command:test --protect tests --rollback-on-failure
```

| Option | Effect |
|---|---|
| `--allow-write` | create, edit, rewrite and move files |
| `--allow-delete` | also delete files |
| `--only GLOB` | nothing outside these paths may be written by the file tools (repeatable) |
| `--protect GLOB` | these paths are read-only; any change to them, including by a command, voids the result (repeatable) |
| `--commands FILE` | commands the model may start by name; it never writes a command line |
| `--allow-exec` | required with `--commands` |
| `--command-timeout S` | per command, default 120 seconds; the whole process tree is killed |
| `--check SPEC` | acceptance criterion (repeatable) |
| `--holdout SPEC` | criterion the model never sees, run once at the end; needs at least one `--check` (repeatable) |
| `--rollback-on-failure` | undo the file writes on any outcome other than `verified`, `checks_passed_non_discriminating` or `model_finished_unverified`, including Ctrl+C |
| `--steps N` | model replies allowed, 1 to 50, default 20 |
| `--think` | let the model reason before each reply; slower |

A holdout is the defence against a model that satisfies the visible test without solving the problem. Keep its
test file outside the workspace, so the model cannot read it. A command named only by `--holdout` is hidden from the
model and cannot be started by it:

```json
{ "test": ["python", "-m", "unittest"], "secret": ["python", "/home/me/holdout/test_edge_cases.py"] }
```

Check kinds: `exists:path`, `absent:path`, `contains:path::text`, `sha256:path::hex`, `command:name`.
The model sees the kind and target of each check, never the expected text or hash. It does see the output of a failing command.

## Reading the result

The exit code is 0 when the mission is verified, or when it finished and you gave no check; 1 when it did not succeed;
2 on a usage or environment error, including the status `failed`; 130 after Ctrl+C.

| `status` | Meaning |
|---|---|
| `verified` | every check passes, at least one was failing before the mission, and protected files are unchanged |
| `checks_passed_non_discriminating` | every check passes, but they already did before the mission, so they prove nothing about it |
| `verification_failed` | the model reported completion and the checks disagree |
| `holdout_failed` | the visible checks pass and a holdout does not: do not trust the change |
| `protected_modified` | a protected file changed; nothing is proven |
| `model_finished_unverified` | no check was given; the answer is only the model's claim |
| `budget_exhausted`, `repeated_action`, `invalid_action` | stopped before success |
| `failed` | environment error, described in `error` |

**`verified` means your checks pass. It does not mean the change is correct.** A model can satisfy a weak test
without solving the problem, for example by special-casing the tested inputs. Read the `diff` field before you keep
the change, and write checks that are hard to satisfy by accident.

## Review and undo

```sh
potklin diff <mission>
potklin rollback <mission>          # refuses if you edited one of the files since
potklin rollback <mission> --force
potklin log <mission>
```

The mission id is printed on standard error as soon as the mission starts, so an interrupted run can still be undone.
Try without `--force` first; it is needed when a write was cut off half-way, and it overwrites later edits. Whatever
cannot be restored is listed under `unrestored`, its previous content stays in the journal, and the exit code is 1.
Rollback covers the file tools only: **whatever a command changed is not recorded and is not undone.** Use version
control for anything you cannot afford to lose.

The journal lives in `~/.potklin/journal.sqlite3`. Its event log holds tool names and outcomes, not file content.
Its checkpoint table does hold the previous content of every file a mission changed, until that mission is rolled back.

## Security model

Enforced by the runtime, whatever the model replies:

- file tools stay inside the workspace and refuse links, junctions and Windows device names such as `NUL`;
- `git` is never searched for in the current directory or the workspace;
- `.git`, `.env`, `.env.*` (except `.env.example`), `.vscode`, `.idea` and `.potklin` cannot be read or written, including
  through Windows aliases such as `.git.` or `GIT~1`;
- no shell and no model-written command line; a program name that resolves inside the workspace is refused;
- commands do not inherit environment variables whose name suggests a secret;
- a file can only be changed after it was read, and only if it has not changed since;
- the model cannot launch desktop applications from a mission.

Not enforced. Assume these are possible:

- **Commands are not sandboxed.** With `--allow-write` and a command that runs workspace code (any test runner), the model
  can run any code as you: read your files, use the network, change things outside the workspace. The name filter on
  environment variables does not stop code from reading credentials on disk. Run such missions only on projects and
  tasks you would let an unreviewed script run on, or declare a command that isolates itself, for example
  `["docker", "run", "--rm", "--network", "none", "-v", "<workspace>:/work", "-w", "/work", "python:3.12", "python", "-m", "unittest"]`.
- **Prompt injection can succeed.** Text in a file can steer the model. Tool results are marked as data, but a local
  model may still obey them; this happened during evaluation. Limit the damage with `--only`, `--protect`,
  `--rollback-on-failure`, and by leaving out `--allow-delete` and `--allow-exec` when the workspace is not yours.
- Path checks are not race-proof against another process changing the workspace during a mission.
- The browser tools give Chromium a dead proxy and perform approved requests themselves, so redirects, WebSockets,
  workers and prefetch cannot reach another origin. This is not an OS network sandbox, and WebRTC is only restricted
  by a Chromium setting that has not been tested here.
- Start the agent with the `potklin` command. From a checkout, `python -P -m potklin` keeps the current directory off
  the module path.
- A browser request that exceeds its time limit is abandoned, but its background thread can linger until the server
  stops sending or the process ends.
- `--only` and `--protect` patterns treat `*` and `?` as wildcards, and `*` also crosses directories.
