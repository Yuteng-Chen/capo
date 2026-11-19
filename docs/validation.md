# v0.1.0 validation

This file records the local release checks. It distinguishes deterministic checks, Agent review and host integration evidence.

## Reproduce

From the repository root, with Python 3.11+ and Node.js 22+:

```sh
python3 scripts/check.py
node tests/isolation-check.mjs
```

The fixture in [synthetic-run.json](../examples/synthetic-run.json) is synthetic. Its identifiers, messages and outcomes are examples, not real Worker events. The isolation check uses a controlled child process in a temporary directory; it does not interrupt a Codex Worker.

## Release results

Local checks on macOS completed for 0.1.0:

| Check | Result and scope |
| --- | --- |
| `python3 scripts/check.py` | Passed: 17 UTF-8 release files, required files, skill metadata, local links, common credential/path patterns and synthetic evidence bindings. Run with Python 3.12.14 and additionally the system Python 3.9.6; the documented development baseline remains 3.11+. This is not a comprehensive secret scanner or full YAML validator. |
| `node tests/isolation-check.mjs` | Passed on Node.js 24.21.0: distinct file identities, late write isolation, symlink/hardlink counterexamples and integration only after observed controlled-child exit. |
| Negative release checks | Temporary-copy mutations for changed artifact content, stale V1 acceptance, invalid carry-forward, broken local link, absolute user path, credential-like text and escaping symlink were rejected. Required-file deletion and an internal symlink were also rejected after review hardening. |
| Experiment cleanup | Normal completion and an injected failure after child creation both cleaned the temporary directory. The injected failure returned nonzero. |
| Skill Creator format validator | Passed for the packaged skill. This extra local check used the installed Skill Creator and its YAML dependency; it is not a prerequisite for the standalone CI commands. |
| Independent protocol review | Six decision scenarios and independent synthetic-fixture/digest arithmetic checks passed. A control-exception ambiguity was found and corrected: user model/cost prohibitions override any stop-message wakeup exception. The reviewer reread the correction and found no remaining release blocker. |

The six reviewed scenarios were unknown inherited models with zero advanced budget; a running Worker plus an unresolved spawn occupying both slots; V2 output changes with an unchanged input fixture; local pause with partially dependent work; a substitute sharing old output through a link; and immediate stop with an unwritable record location. These were Agent decision exercises, not actual Codex host fault injection.

The examples were generated as public synthetic data. Historical private transcripts, identifiers and local paths are excluded. The release contains no symbolic links. The workflow pins official action commits and runs offline project checks after acquiring its tools; the GitHub runner itself needs network access for action/tool setup. No cloud run has been claimed.

## Limits

- A successful Skill format check establishes parseable metadata and valid references, not reliable Agent behavior.
- Script checks validate deterministic artifacts and invariants, not natural-language compliance.
- The scenarios in [scenarios.md](../tests/scenarios.md) require an independent human or Agent review; they are not an automated runtime scheduler test suite.
- No real lost Codex Worker, forced interruption or OS-enforced read-only reviewer has been tested for this release.
- No cloud GitHub Actions run or GitHub publication has been performed. Local commands matching the workflow are the evidence available here.
- Historical testing found a model accepted by desktop native delegation but rejected by a standalone CLI account. Each host and entrypoint must verify its own capabilities; listed models are not universal availability guarantees.
