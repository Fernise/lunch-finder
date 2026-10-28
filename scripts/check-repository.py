#!/usr/bin/env python3
"""Check exact tracked/index contents before a public commit. Never print values."""
import json
import pathlib
import re
import subprocess
import sys


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def main():
    paths = [name.decode() for name in git("ls-files", "-z").split(b"\0") if name]
    if not paths:
        print("No tracked files were found; stage the reviewed source first.")
        return 1
    private = {"data", "logs", "backups", "private", "research", "internal", ".private", ".private-backups", "node_modules", ".venv", "__pycache__", ".wrangler", ".next", ".gradle", ".idea"}
    extensions = {".sqlite", ".sqlite3", ".db", ".key", ".pem", ".p12", ".pfx", ".jks", ".keystore", ".log", ".apk", ".aab", ".zip", ".brisaenc"}
    findings = []
    for name in paths:
        path = pathlib.PurePosixPath(name)
        base = path.name
        private_procedure = (
            "runbook" in name.lower()
            or name.startswith("deploy/vps/")
            or name in {"android/STORE-LISTING.md", "android/DATA-SAFETY.md", "infra/realtime-relay/activate-reliability.sh"}
            or re.search(r"^scripts/(?:package|check)-.*-release.*\.py$", name)
            or name == "scripts/check-identity-host.py"
        )
        if private_procedure:
            findings.append({"path": name, "reason": "private_operational_procedure"})
            continue
        if any(part in private for part in path.parts) or path.suffix.lower() in extensions or (base.startswith((".env", ".dev.vars")) and not base.endswith(".example")) or base.endswith((".env", ".env.save")):
            findings.append({"path": name, "reason": "private_or_generated_path"})
            continue
        info = git("ls-files", "--stage", "--", name)
        if info.startswith(b"120000"):
            findings.append({"path": name, "reason": "unreviewed_symlink"})
            continue
        content = git("show", ":" + name)
        if len(content) > 5 * 1024 * 1024:
            findings.append({"path": name, "reason": "oversized_artifact"})
        if base in {".env.example", ".dev.vars.example"}:
            for line in content.decode().splitlines():
                if line.lstrip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if re.search(r"(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY|ANON_KEY|CHAT_ID|RHL_PASS)$", key.strip()) and value.strip().strip("\"'"):
                    findings.append({"path": name, "reason": "credential_example_must_be_blank", "setting": key.strip()})
    print(json.dumps({"passed": not findings, "tracked_files_checked": len(paths), "findings": findings, "values_displayed": False}, indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
