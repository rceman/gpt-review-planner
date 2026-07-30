#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path); p.add_argument("--evidence",type=Path); a=p.parse_args()
if (a.manifest is None)==(a.evidence is None): p.error("provide exactly one input")
value=json.loads((a.manifest or a.evidence).read_text())
if a.manifest:
 c=value.get("compatibility",{})
 ok=c.get("scope")=="none" and c.get("authorized") is False and c.get("supported_legacy_versions")==[] and c.get("direction")=="none"
else:
 ok=value.get("compatibility_scope")=="none" and value.get("compatibility_authorized") is False and all(value.get(k)==[] for k in ("compatibility_features_added","legacy_paths_added","fallbacks_added","migration_behavior_added"))
if not ok:
 print("ERROR: unauthorized compatibility declaration",file=sys.stderr); raise SystemExit(1)
print("COMPATIBILITY_DECLARATION_OK")
