#!/bin/sh
set -eu
umask 077
mkdir -p "$HOME" /data/profile /data/agents /workspace
if [ ! -w "$HOME" ] || [ ! -w /data/profile ] || [ ! -w /workspace ]; then
  echo 'Persistent directories must be writable by the configured UID/GID.' >&2
  exit 1
fi
# Pairing links are credentials: never print them into container logs.
exec orca serve --bind 0.0.0.0 --port 6768 --pairing-address "${ORCA_PAIRING_ADDRESS:-127.0.0.1}" --no-pairing --refuse-public
