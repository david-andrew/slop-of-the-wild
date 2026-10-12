#!/usr/bin/env python3
"""Retrieve the pinned response-research sources and check their exact bytes.

This verifies provenance, not whether a field establishes movement response semantics.
Downloads stay in build/movement-reference-sources/. No game render occurs.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="download even cached sources")
    args = parser.parse_args()
    audit = json.loads((base / "movement-response-audit.json").read_text())
    cache = base.parent.parent / "build" / "movement-reference-sources"
    verified = 0
    total_bytes = 0
    for source in audit["files"]:
        destination = cache / source["repository"] / source["commit"] / source["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if args.refresh or not destination.exists():
            temporary = destination.with_name(destination.name + ".part")
            try:
                subprocess.run(
                    ["curl", "-fsSL", "--max-time", "45", source["raw_url"], "-o", str(temporary)],
                    check=True,
                )
                content = temporary.read_bytes()
                if len(content) != source["bytes"] or hashlib.sha256(content).hexdigest() != source["sha256"]:
                    raise SystemExit(f"FAIL downloaded source hash: {source['id']}")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        content = destination.read_bytes()
        if len(content) != source["bytes"] or hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise SystemExit(f"FAIL cached source hash: {source['id']} (use --refresh)")
        verified += 1
        total_bytes += len(content)
        print(f"PASS {source['id']}: {source['sha256']}")
    print(f"PASS {verified} pinned sources, {total_bytes} bytes; response semantics remain unverified")


if __name__ == "__main__":
    main()
