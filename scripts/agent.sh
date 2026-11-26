#!/bin/sh
# ASVS 1.2.5: fixed package allowlist; no eval or arbitrary shell construction.
set -eu
umask 077
case "${1:-}" in
  codex) package=@openai/codex ;;
  claude) package=@anthropic-ai/claude-code ;;
  *) echo 'Usage: orca-agent codex|claude exact-version' >&2; exit 2 ;;
esac
version=${2:-}
case "$version" in ''|*[!0-9A-Za-z.+-]*) echo 'An exact numeric release version is required.' >&2; exit 2;; esac
case "$version" in [0-9]*.[0-9]*.[0-9]*) ;; *) exit 2;; esac
npm install --global --save-exact "$package@$version"
printf '%s %s\n' "$package" "$version" >> /data/agents/installed-versions.txt
