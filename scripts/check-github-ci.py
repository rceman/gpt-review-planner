#!/usr/bin/env python3
"""Capability-aware, exact-SHA GitHub Actions status check."""
from __future__ import annotations
import argparse, json, os, sys, time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STATES = {"success", "pending", "failed", "cancelled", "timed_out", "action_required", "neutral", "skipped", "no_run", "unavailable", "not_applicable", "invalid_response"}
EXIT = {"success": 0, "not_applicable": 0, "pending": 2, "failed": 3, "cancelled": 3, "timed_out": 3, "action_required": 3, "neutral": 3, "skipped": 3, "no_run": 0, "unavailable": 0, "invalid_response": 5}

def result(args, state, message, _quiet=False, **values):
    blocking = state in {"failed", "cancelled", "timed_out", "action_required", "neutral", "skipped", "invalid_response"} or (state in {"no_run", "unavailable"} and args.policy == "required") or state == "pending"
    data = {"schema_version": 1, "repository": args.repository, "sha": args.sha, "policy": args.policy, "state": state, "blocking": blocking, "source": "policy" if state == "not_applicable" else "github-actions-rest", "run_id": None, "job_id": None, "run_url": None, "job_url": None, "workflow": None, "event": None, "status": None, "conclusion": None, "checked_sha": None, "message": message}
    data.update(values)
    if not _quiet:
        if args.format == "json": print(json.dumps(data, sort_keys=True))
        else: print(f"{state}: {message}")
    return data

def fetch(url, token):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "gpt-review-planner-ci-check"}
    if token: headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response: return json.loads(response.read().decode("utf-8"))

def classify(run, job):
    conclusion = run.get("conclusion")
    status = run.get("status")
    if status != "completed": return "pending"
    if conclusion == "success": return "success"
    if conclusion == "cancelled": return "cancelled"
    if conclusion == "timed_out": return "timed_out"
    if conclusion == "action_required": return "action_required"
    if conclusion in {"neutral", "skipped"}: return conclusion
    return "failed"

def main():
    p = argparse.ArgumentParser(); p.add_argument("--repository", required=True); p.add_argument("--sha", required=True); p.add_argument("--policy", choices=["auto", "required", "optional", "disabled"], default="auto"); p.add_argument("--format", choices=["text", "json"], default="text"); p.add_argument("--wait", action="store_true"); p.add_argument("--timeout", type=int, default=1800); p.add_argument("--interval", type=int, default=15); p.add_argument("--api-url", default="https://api.github.com"); p.add_argument("--workflow"); p.add_argument("--event", default="push"); a=p.parse_args()
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repository) or not re.fullmatch(r"[0-9a-f]{40}", a.sha):
        result(a, "invalid_response", "repository or SHA format is invalid"); return 5
    if a.timeout <= 0 or a.interval < 1: result(a, "invalid_response", "timeout must be positive and interval at least 1"); return 5
    if a.policy == "disabled": result(a, "not_applicable", "remote CI is disabled by policy"); return 0
    token=os.environ.get("GITHUB_TOKEN"); base=a.api_url.rstrip("/"); runs_url=f"{base}/repos/{a.repository}/actions/runs?head_sha={a.sha}&per_page=100"
    deadline=time.monotonic()+a.timeout
    while True:
        try: payload=fetch(runs_url, token)
        except HTTPError as e:
            state="unavailable" if e.code in {401,403,404} else "invalid_response"; result(a,state,f"GitHub Actions query returned HTTP {e.code}"); return 4 if state=="unavailable" and a.policy=="required" else (0 if state=="unavailable" else 5)
        except (URLError, OSError, json.JSONDecodeError) as e:
            result(a,"unavailable",f"GitHub Actions query unavailable: {e}"); return 4 if a.policy=="required" else 0
        if not isinstance(payload,dict) or not isinstance(payload.get("workflow_runs"),list): result(a,"invalid_response","GitHub Actions response has invalid workflow_runs"); return 5
        candidates=[r for r in payload["workflow_runs"] if isinstance(r,dict) and r.get("head_sha")==a.sha and (not a.workflow or a.workflow in str(r.get("name")) or a.workflow in str(r.get("path"))) and (not a.event or not r.get("event") or r.get("event")==a.event)]
        if not candidates:
            if a.wait and time.monotonic() < deadline:
                time.sleep(min(a.interval, max(0, deadline-time.monotonic())))
                continue
            state = "timed_out" if a.wait else "no_run"
            if state == "timed_out":
                result(a, state, "timed out waiting for a matching exact-SHA workflow run")
                return 6
            result(a,"no_run","no matching exact-SHA workflow run was found")
            return 0 if a.policy in {"auto","optional"} else 4
        run=sorted(candidates, key=lambda item: (str(item.get("created_at", "")), int(item.get("id", 0))), reverse=True)[0]
        state=classify(run, None)
        values={"run_id":run.get("id"),"run_url":run.get("html_url"),"workflow":run.get("name") or run.get("path"),"event":run.get("event"),"status":run.get("status"),"conclusion":run.get("conclusion"),"checked_sha":run.get("head_sha")}
        try: jobs=fetch(f"{base}/repos/{a.repository}/actions/runs/{run['id']}/jobs?per_page=100", token)
        except (HTTPError, URLError, OSError, json.JSONDecodeError, KeyError) as e:
            values["message"] = f"exact-SHA run {run.get('id')} resolved as {state}; job metadata unavailable: {e}"
            data=result(a,state,values.pop("message"),_quiet=state=="pending" and a.wait,**values)
            if state=="pending" and a.wait and time.monotonic()<deadline: time.sleep(min(a.interval,max(0,deadline-time.monotonic()))); continue
            if state=="pending" and a.wait: return 6
            return EXIT[state]
        if not isinstance(jobs, dict) or not isinstance(jobs.get("jobs"), list):
            message=f"exact-SHA run {run.get('id')} resolved as {state}; job metadata unavailable: malformed jobs response"
            result(a,state,message,_quiet=state=="pending" and a.wait,**values)
            if state=="pending" and a.wait and time.monotonic()<deadline: time.sleep(min(a.interval,max(0,deadline-time.monotonic()))); continue
            if state=="pending" and a.wait: return 6
            return EXIT[state]
        job=(jobs.get("jobs") or [None])[0]
        if job: values.update(job_id=job.get("id"),job_url=job.get("html_url"))
        data=result(a,state,f"exact-SHA run {run.get('id')} is {state}",_quiet=state=="pending" and a.wait,**values)
        if state=="pending" and a.wait and time.monotonic()<deadline: time.sleep(min(a.interval,max(0,deadline-time.monotonic()))); continue
        if state=="pending" and a.wait: return 6
        return EXIT.get(state,5) if state not in {"no_run","unavailable"} else (0 if a.policy in {"auto","optional"} else 4)
if __name__ == "__main__": sys.exit(main())
