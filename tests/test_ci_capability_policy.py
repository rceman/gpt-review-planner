import json, os, subprocess, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; TOOL=ROOT/'scripts/check-github-ci.py'; SHA='a'*40

class Handler(BaseHTTPRequestHandler):
    payload={}; calls=0; headers={}
    def do_GET(self):
        type(self).calls += 1; type(self).headers=dict(self.headers)
        body=json.dumps(type(self).payload).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

class CICapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=cls.server.serve_forever,daemon=True).start(); cls.api=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls): cls.server.shutdown()
    def setUp(self): Handler.calls=0; Handler.payload={'workflow_runs':[]}; os.environ.pop('GITHUB_TOKEN',None)
    def run_tool(self, policy='auto', fmt='json', extra=(), sha=SHA, env=None):
        e=os.environ.copy(); e.update(env or {}); p=subprocess.run([sys.executable,str(TOOL),'--repository','owner/repo','--sha',sha,'--policy',policy,'--format',fmt,'--api-url',self.api,*extra],capture_output=True,text=True,env=e); return p
    def run_data(self, **kw): return json.loads(self.run_tool(**kw).stdout)
    def test_disabled_zero_requests(self): self.assertEqual(self.run_data(policy='disabled')['state'],'not_applicable'); self.assertEqual(Handler.calls,0)
    def test_success_exact_sha(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'success','name':'Validate','event':'push','html_url':'u'}]}; d=self.run_data(); self.assertEqual(d['state'],'success'); self.assertEqual(d['checked_sha'],SHA)
    def test_wrong_sha_rejected(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':'b'*40,'status':'completed','conclusion':'success'}]}; self.assertEqual(self.run_data()['state'],'no_run')
    def test_pending_without_wait(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'queued','conclusion':None}]}; p=self.run_tool(); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['state'],'pending')
    def test_pending_wait_timeout(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'queued','conclusion':None}]}; p=self.run_tool(extra=('--wait','--timeout','1','--interval','1')); self.assertEqual(p.returncode,6)
    def test_failure_required(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'failure'}]}; self.assertEqual(self.run_tool(policy='required').returncode,3)
    def test_failure_auto(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'failure'}]}; self.assertEqual(self.run_tool(policy='auto').returncode,3)
    def test_failure_optional(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'failure'}]}; self.assertEqual(self.run_tool(policy='optional').returncode,3)
    def test_failure_disabled_no_query(self): self.assertEqual(self.run_tool(policy='disabled').returncode,0); self.assertEqual(Handler.calls,0)
    def test_auto_no_run_nonblocking(self): self.assertEqual(self.run_tool(policy='auto').returncode,0)
    def test_optional_no_run_nonblocking(self): self.assertEqual(self.run_tool(policy='optional').returncode,0)
    def test_required_no_run_blocking(self): self.assertEqual(self.run_tool(policy='required').returncode,4)
    def test_text_output(self): p=self.run_tool(fmt='text'); self.assertIn('no_run:',p.stdout)
    def test_json_schema_fields(self): d=self.run_data(); self.assertEqual(set(d),{'schema_version','repository','sha','policy','state','blocking','source','run_id','job_id','run_url','job_url','workflow','event','status','conclusion','checked_sha','message'})
    def test_no_cache_headers(self): self.run_tool(); self.assertEqual(Handler.headers['Cache-Control'],'no-cache'); self.assertEqual(Handler.headers['Pragma'],'no-cache'); self.assertIn('application/vnd.github+json',Handler.headers['Accept'])
    def test_token_header_only_when_set(self): self.run_tool(); self.assertNotIn('Authorization',Handler.headers); self.run_tool(env={'GITHUB_TOKEN':'secret'}); self.assertEqual(Handler.headers['Authorization'],'Bearer secret')
    def test_explicit_policy_not_visibility(self): self.assertEqual(self.run_data(policy='auto')['policy'],'auto'); self.assertEqual(self.run_data(policy='disabled')['policy'],'disabled')
    def test_event_filter(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'success','event':'pull_request'}]}; self.assertEqual(self.run_data()['state'],'no_run')
    def test_workflow_filter(self): Handler.payload={'workflow_runs':[{'id':1,'head_sha':SHA,'status':'completed','conclusion':'success','event':'push','name':'Other'}]}; self.assertEqual(self.run_data(extra=('--workflow','Validate'))['state'],'no_run')
    def test_malformed_json(self): Handler.payload=[]; self.assertEqual(self.run_tool().returncode,5)
    def test_existing_manifests_remain_valid(self): self.assertEqual(subprocess.run([sys.executable,str(ROOT/'scripts/validate-patch-pack.py'),'examples/gateway-compatible-patch-pack'],capture_output=True).returncode,0)

if __name__=='__main__': unittest.main()
