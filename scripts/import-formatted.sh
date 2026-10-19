#!/usr/bin/env bash
# Import immutable sandbox output, never new paths or executable Git metadata.
set -euo pipefail

baseline=$1
formatted=$2
destination=$3

# Do not resolve the output root: it could itself be a malicious symlink.
[[ -d $formatted && ! -L $formatted ]] || exit 1
# Reject symlinks (including directory ancestors), devices, FIFOs and sockets.
# Both trees are immutable Nix store paths, so validation cannot race a writer.
invalid=$(find "$formatted" ! -type d ! -type f -print -quit)
[[ -z $invalid ]] || { echo "Unsupported formatter output: $invalid" >&2; exit 1; }

# The allowlist comes from the trusted baseline, not the formatter. Copy only
# file contents, retaining the checkout's permissions and all non-Nix files.
find "$baseline" -type f -name '*.nix' -printf '%P\0' |
  rsync --from0 --files-from=- --existing --no-perms "$formatted/" "$destination/"
