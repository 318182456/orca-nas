#!/usr/bin/env python3
"""Pinned official-release upgrade. Run on the NAS from the project directory."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent

def run(*args, env=None):
    # ASVS 1.2.5: subprocess argument arrays, never shell=True.
    return subprocess.run(args, cwd=ROOT, env=env, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="Exact official release, e.g. 1.4.277")
    parser.add_argument("sha256", help="Verified official linux-x64 artifact checksum")
    parser.add_argument("--apply", action="store_true", help="Stop, back up, then replace the service")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("invalid version")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.sha256):
        parser.error("invalid checksum")
    os.umask(0o077)
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    artifact = cache / "orca-server-linux-x64.tar.gz"
    if not artifact.exists() or hashlib.sha256(artifact.read_bytes()).hexdigest() != args.sha256.lower():
        url = f"https://github.com/stablyai/orca/releases/download/v{args.version}/orca-server-linux-x64.tar.gz"
        temporary = cache / "download.part"
        with urllib.request.urlopen(url, timeout=60) as src, temporary.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != args.sha256.lower():
            temporary.unlink()
            raise SystemExit("Checksum mismatch; running service was not changed")
        temporary.replace(artifact)
    env = dict(os.environ, ORCA_VERSION=args.version, ORCA_SHA256=args.sha256.lower())
    run("docker", "compose", "build", env=env)
    if not args.apply:
        print("Candidate image built. Repeat with --apply after stopping agent tasks.")
        return
    backup = ROOT / "backups" / time.strftime("%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, mode=0o700)
    run("docker", "compose", "stop", "orca")
    try:
        with tarfile.open(backup / "data.tar.gz", "w:gz") as archive:
            for name in ("data", ".env"):
                archive.add(ROOT / name, arcname=name)
    except BaseException:
        run("docker", "compose", "start", "orca")
        raise
    config = ROOT / ".env"
    text = config.read_text()
    for key, value in (("ORCA_VERSION", args.version), ("ORCA_SHA256", args.sha256.lower())):
        line = f"{key}={value}"
        pattern = rf"(?m)^{key}=.*$"
        text = re.sub(pattern, line, text) if re.search(pattern, text) else text.rstrip() + "\n" + line + "\n"
    temporary = ROOT / ".env.next"
    temporary.write_text(text)
    temporary.chmod(0o600)
    temporary.replace(config)
    run("docker", "compose", "up", "-d", "--no-build", "orca")
    print(f"Started {args.version}; restricted rollback backup: {backup}")
    print("Verify pairing, terminal and agent access before deleting the old image/backup.")
    print("Do not downgrade an upgraded profile without restoring its matching data backup.")

if __name__ == "__main__":
    main()
