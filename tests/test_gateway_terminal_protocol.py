import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(rel,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

class GatewayTerminalProtocolTests(unittest.TestCase):
    def setUp(self): self.validator=load('scripts/validate-gateway-agent-result.py','gateway_result_validator')
    def write(self,root,value):
        path=root/'agent-result.json'; path.write_text(json.dumps(value)+'\n'); return path
    def base(self,status='failed'):
        return {'schema_version':2,'task_id':'task_001','status':status,'summary':'bounded summary','details':[],'gates':[],'deviations':[]}
    def test_failed_minimal_is_valid(self):
        with tempfile.TemporaryDirectory() as d: self.assertEqual(self.validator.validate(self.write(Path(d),self.base()),'task_001',None),[])
    def test_needs_revision_requires_next_action(self):
        with tempfile.TemporaryDirectory() as d:
            value=self.base('needs_gpt_revision'); codes={x['code'] for x in self.validator.validate(self.write(Path(d),value),'task_001',None)}; self.assertIn('missing_next_action',codes)
    def test_unknown_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            value=self.base(); value['repository']='rceman/example'; codes={x['code'] for x in self.validator.validate(self.write(Path(d),value),'task_001',None)}; self.assertIn('unknown_field',codes)
    def test_duplicate_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'agent-result.json'; path.write_text('{"schema_version":2,"schema_version":2}\n'); codes={x['code'] for x in self.validator.validate(path,'task_001',None)}; self.assertIn('invalid_json',codes)
    def test_succeeded_requires_exact_manifest_gates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); manifest=root/'manifest.json'; manifest.write_text(json.dumps({'gates':[{'id':'one'},{'id':'two'}]}))
            value=self.base('succeeded'); value.update({'implementation_commit':'1'*40,'evidence_commit':'2'*40,'gates':[{'id':'one','status':'pass','exit':0,'summary':'ok'}]})
            codes={x['code'] for x in self.validator.validate(self.write(root,value),'task_001',manifest)}; self.assertIn('gate_identity_mismatch',codes)
    def test_patch_validator_requires_terminal_protocol(self):
        module=load('scripts/validate-patch-pack.py','patch_validator'); self.assertIn('TERMINAL_OUTPUT_PROTOCOL',module.REQUIRED_HANDOFF_HEADINGS)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'AGENT_HANDOFF.md'; headings=[h for h in module.REQUIRED_HANDOFF_HEADINGS if h!='TERMINAL_OUTPUT_PROTOCOL']; path.write_text('# AGENT_HANDOFF\n\n'+'\n\n'.join(f'## {h}\n\ncontent' for h in headings)+'\n')
            findings=[]; warnings=[]; module.validate_handoff(path,None,findings,warnings); self.assertIn('missing_agent_handoff_heading',{x.code for x in findings})
    def test_template_and_docs_define_protocol(self):
        template=(ROOT/'templates/executable-patch-pack/AGENT_HANDOFF.md').read_text(); self.assertIn('## TERMINAL_OUTPUT_PROTOCOL',template); self.assertIn('complete-task',template); self.assertIn('agent-result.json',template)
        docs=(ROOT/'docs/GATEWAY_TASK_PROTOCOL.md').read_text(); self.assertIn('inbox/<task_id>.plan.json',docs); self.assertIn('Interactive Airelay/Codex text',docs)

if __name__=='__main__': unittest.main()
