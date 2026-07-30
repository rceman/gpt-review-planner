#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,subprocess
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument("archive",type=Path); p.add_argument("--repo",required=True,type=Path); p.add_argument("--archive-sha256")
a=p.parse_args()
h=hashlib.sha256(a.archive.read_bytes()).hexdigest()
runner=Path(__file__).with_name("gpt-patch-pack-runner-v1.py")
raise SystemExit(subprocess.run(["python3",str(runner),"--archive",str(a.archive.resolve()),"--archive-sha256",a.archive_sha256 or h,"--repo",str(a.repo.resolve())]).returncode)
