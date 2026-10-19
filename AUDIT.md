# Performance and security audit

Base: NixOS/nixfmt `1f2017a`. Local branch: `audit/performance-security`.
Three parallel read-only audits covered parsing, rendering, and security;
two independent follow-up reviews found no concrete introduced bugs.
Nothing was pushed or published. This is a bounded audit, not a security certification.

## Fixes (one commit per issue)

| Commit | Change |
| --- | --- |
| `240fa93` | Concatenate adjacent parser text parts once, preserving interpolation boundaries. |
| `91c4cfb` | Import only trusted baseline-listed regular Nix files from sandboxed CI output. Reject symlinks/special files; never import Git metadata. |
| `1b048dc` | Convert indented-string escapes with one concatenation, preserving escape precedence. |
| `8947a62` | Skip directory symlinks during recursive discovery, avoiding escapes and cycles. |
| `25ef55c` | Reject inline directive candidates without scanning the remainder of the line. |
| `d22d2d3` | Advance a source suffix between directives; capture disabled-region suffixes when opened. |
| `473ada2` | Flatten operator trees with a tail accumulator and share the operand list. |
| `1cfa622` | Reuse `someP` to scan ordinary string text in chunks rather than allocating per character. |
| `c11f02a` | Reuse `openTempFile` for private initial temporary-file permissions. |

The CI vulnerability was reproduced locally with a harmless marker: arbitrary
formatter output could install a Git hook executed by the host's later commit.
The replacement uses existing `find`/`rsync` primitives and a trusted file list.
Both store trees must be immutable; this is not an importer for mutable hostile trees.
Directory-link escape and ACL loss were also reproduced locally.

## Measurements

Linux, one process/core, wall-clock seconds; isolated runs, not statistical
confidence intervals. Peak RSS is from `wait4` in KiB. Benchmark verification
runs are separate from timed runs. Unless stated otherwise, before is upstream.

| Input | Size | Before | After |
| --- | ---: | ---: | ---: |
| Path components | 40,000 | 0.179 s | 0.145 s |
| Single-line indented string (escape fix only) | 160,000 characters | 0.341 s | 0.099 s |
| Inline directive comments | 4,000 | 2.574 s | 0.067 s |
| Standalone directives and list items | 160,000 | 26.542 s | 3.394 s |
| `&&` operands | 8,000 | 0.511 s | 0.177 s |
| Ordinary string, before/after bulk scanning | 1,000,000 characters | 0.702 s | 0.167 s |
| Same string, peak RSS | 1,000,000 characters | 171,884 KiB | 20,340 KiB |

Reproduce with a built executable, choosing a case and geometric sizes:

```sh
python3 test/performance.py /path/to/nixfmt --case inline-directives --sizes 1000 2000 4000
```

The harness also checks parse preservation and idempotence with `--verify`.
Raw measurements and baseline/final executable paths are retained in the parent
audit directory (`../*-before.jsonl`, `../*-after.jsonl`, `../baseline-profile.jsonl`).

## Validation

- Full snapshot, invalid-input, formatting-verification and mergetool tests.
- Five sandbox-import tests, including hooks, Git config, attributes, unexpected
  files, root/directory/file symlinks, and FIFOs; two CLI symlink regressions.
- Nix checks: `tests`, `treefmt`, `hlint`, `cabal-check`, and `reuse`.
- Low-level atomic creation/mode/rollback/cleanup regression: old primitive fails,
  patched primitive passes. Optional developer-shell invocation:

```sh
d=$(mktemp -d)
runghc -imain test/atomic.hs "$d"
rm -rf "$d"
```

Validation builds used frozen worktrees after an early run caught edits mid-read.
No format changes were intended; new golden outputs were generated using upstream.

## Remaining issues and limits

- **ACL/extended-attribute preservation is unresolved.** Atomic replacement copies
  mode/ownership but loses POSIX ACLs. A restrictive ACL with an ACL mask of `r--`
  can become a plain group-readable file. Verified with `setfacl`/`getfacl`.
  A portable metadata-preservation policy/API is needed; do not use in-place
  formatting on ACL-protected confidential files meanwhile (format via stdin).
- **Long selector chains remain quadratic.** Upstream `x.a.a...` measured 2.29 s,
  9.43 s, and 37.85 s at 10k/20k/40k selectors. `selector`'s negative `path`
  lookahead repeatedly scans path-character suffixes. Changing this safely needs
  dedicated path/selection ambiguity tests; the reproducer remains in the harness.
- A proposed IR text-merging rewrite was discarded: end-to-end selector timings
  did not improve and interpolation timings regressed. No `Predoc.hs` change remains.
- Priority-group discovery, very deep nesting, and wide-line fitting merit further
  profiling; no unmeasured redesign was applied.
- Directory-link protection is not a general containment guarantee: explicit
  paths containing symlink ancestors still resolve normally. Directory traversal
  remains deprecated. Existing ACL/xattr limitations and file-system races are
  not claimed solved by private temporary-file creation.
- Static linking, non-Linux platforms, and a live GitHub Actions deployment were
  not validated. Tests reproduce the CI trust boundary locally without secrets.
