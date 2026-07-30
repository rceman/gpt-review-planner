#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,re,sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument("--archive",required=True,type=Path); p.add_argument("--sha256-file",required=True,type=Path); a=p.parse_args()
if not re.fullmatch(r"patch-[0-9]{8}-[0-9]{6}-[a-z0-9]+(?:-[a-z0-9]+){0,2}\.tar\.gz",a.archive.name):
 print("invalid archive basename",file=sys.stderr); raise SystemExit(1)
expected=f"{hashlib.sha256(a.archive.read_bytes()).hexdigest()}  {a.archive.name}"
if a.sha256_file.name!=a.archive.name+".sha256" or a.sha256_file.read_text().splitlines()!=[expected]:
 print("invalid sidecar",file=sys.stderr); raise SystemExit(1)
print("PATCH_PACK_DELIVERY_OK")
