#!/usr/bin/env python3
"""NAS scheduled pull, idle check, restricted backup and health-based rollback."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import stat
import time

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "ghcr.io/318182456/orca-nas:stable"

def command(*args, env=None):
    return subprocess.check_output(args, cwd=ROOT, env=env, text=True, stderr=subprocess.STDOUT, timeout=900 if args[:2] == ("docker", "pull") else 120).strip()

def inspect(target):
    return json.loads(command("docker", "inspect", target))[0]

def ignore_runtime(directory, names):
    # Stopped runtimes may leave sockets/FIFOs; only persistent files belong in backups.
    skipped = []
    for name in names:
        mode = (Path(directory) / name).lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
            skipped.append(name)
    return skipped

def clone_tree(source, target):
    shutil.copytree(source, target, symlinks=True, ignore=ignore_runtime)
    # copy2 does not preserve ownership. Restore it for non-root container access.
    for directory, folders, files in os.walk(target, followlinks=False):
        for path in [Path(directory)] + [Path(directory) / name for name in folders + files]:
            original = source / path.relative_to(target)
            info = original.lstat()
            os.lchown(path, info.st_uid, info.st_gid)

def set_image(value):
    path = ROOT / ".env"
    text = path.read_text()
    line = "ORCA_IMAGE=" + value
    text = re.sub(r"(?m)^ORCA_IMAGE=.*$", line, text) if re.search(r"(?m)^ORCA_IMAGE=", text) else text.rstrip() + "\n" + line + "\n"
    temporary = ROOT / ".env.next"
    temporary.write_text(text)
    temporary.chmod(0o600)
    temporary.replace(path)

PROXY_KEYS = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"}


def start(previous_environment):
    # ASVS 1.2.5: pass literals through the process environment, never shell/env-file interpolation.
    # .env values (including empty values) and the updater's own environment take precedence.
    local_keys = set(re.findall(r"(?m)^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", (ROOT / ".env").read_text()))
    environment = dict(os.environ)
    for entry in previous_environment:
        key, separator, value = entry.partition("=")
        if separator and key in PROXY_KEYS and key not in environment and key not in local_keys:
            if "\x00" in value:
                raise RuntimeError("Invalid proxy environment; update cancelled")
            environment[key] = value
    command("docker", "compose", "up", "-d", "--no-build", "orca", env=environment)


def main():
    os.umask(0o077)
    os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + os.environ.get("PATH", "")
    lock = (ROOT / ".update.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another updater is active; skipped")
        return
    old = inspect("orca")
    # Defer instead of interrupting recognized active CLI processes.
    processes = command("docker", "exec", "orca", "ps", "-eo", "args")
    if re.search(r"(?im)(?:^|[/\s])(?:codex|claude|agy|opencode)(?:[\s/]|$)", processes):
        print("Agent process detected; update deferred")
        return
    command("docker", "pull", IMAGE)
    candidate = inspect(IMAGE)["Id"]
    if old["Image"] == candidate:
        print("Image unchanged")
        return
    current_version = command("docker", "exec", "orca", "orca", "--version")
    next_version = command("docker", "run", "--rm", "--network", "none", "--entrypoint", "orca", candidate, "--version")
    def version(value):
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
            raise RuntimeError("Unexpected version format; no changes applied")
        return tuple(map(int, value.split(".")))
    if version(next_version) < version(current_version):
        raise RuntimeError("Refusing automatic downgrade")
    backup = ROOT / "backups" / time.strftime("%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, mode=0o700)
    command("docker", "compose", "stop", "orca")
    try:
        clone_tree(ROOT / "data", backup / "data")
        shutil.copy2(ROOT / ".env", backup / ".env")
        (backup / "previous-image.txt").write_text(old["Image"] + "\n")
    except BaseException:
        command("docker", "compose", "start", "orca")
        raise
    try:
        set_image(IMAGE)
        start(old["Config"].get("Env", []))
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            state = inspect("orca")["State"]
            if state.get("Health", {}).get("Status") == "healthy":
                print("Updated " + current_version + " -> " + next_version)
                print("Backup: " + str(backup))
                return
            if state.get("Status") in ("exited", "dead"):
                break
            time.sleep(3)
        raise RuntimeError("New container failed health verification")
    except BaseException:
        command("docker", "compose", "stop", "orca")
        failed = backup / "failed-data"
        (ROOT / "data").rename(failed)
        clone_tree(backup / "data", ROOT / "data")
        shutil.copy2(backup / ".env", ROOT / ".env")
        set_image(old["Image"])
        start(old["Config"].get("Env", []))
        print("Rolled back to the previous image and matching data; failed data preserved")
        raise

if __name__ == "__main__":
    main()
