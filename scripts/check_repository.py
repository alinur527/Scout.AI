"""Scan target Git history for common credentials and forbidden committed artifacts.

Heuristic check, not a guarantee of absence. Never print matched credential values.
"""

import re
import subprocess


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    findings = []
    patterns = {
        "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "GitHub token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b",
        "AWS access key": rb"\bAKIA[A-Z0-9]{16}\b",
        "credentialed database URL": rb"postgres(?:ql)?(?:\+\w+)?://[^\s:/]+:[^\s@]+@",
        "literal JWT secret": rb"(?:JWT_SECRET_KEY|SECRET_KEY)\s*=\s*[\"'][^\"'\r\n]{8,}[\"']",
    }
    # Every reachable history blob is inspected once, without bringing old upstream history into the target.
    for row in git("rev-list", "--objects", "--all").decode().splitlines():
        oid, _, path = row.partition(" ")
        if not path or git("cat-file", "-t", oid).strip() != b"blob":
            continue
        if (
            path.endswith((".pt", ".mp4", ".mov", ".avi", ".db"))
            or path.rsplit("/", 1)[-1] == ".env"
        ):
            findings.append((path, "forbidden artifact"))
        content = git("cat-file", "blob", oid)
        for name, pattern in patterns.items():
            if re.search(pattern, content):
                # The checker's own pattern strings and documentation placeholders are not credentials.
                if path.endswith("check_repository.py"):
                    continue
                findings.append((path, name))
    print(f"Scanned reachable Git history; findings: {len(findings)}")
    for path, name in sorted(set(findings)):
        print(f"{path}: {name}")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
