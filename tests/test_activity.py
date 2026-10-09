import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from activity import Activity,clean_log

class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.activity=Activity(self.base)
    def tearDown(self):self.temp.cleanup()
    def state(self,jobs,**extra):
        return dict(timestamp='2026-10-09T12:00:00+00:00',active=jobs,logs='Starting Valheim\nDownloading',games=[{'name':'Valheim','status':'downloading'}],**extra)
    def test_running_session_survives_restart_and_keeps_original_start(self):
        self.activity.observe(self.state(['job']))
        first=self.activity.list()[0]
        restarted=Activity(self.base);restarted.observe(self.state(['job']))
        self.assertEqual(restarted.list()[0]['id'],first['id'])
        restarted.observe(self.state([]))
        self.assertEqual(restarted.list()[0]['status'],'ended')
        self.assertEqual(len(restarted.list()),1)
    def test_failed_managed_session_retains_sanitized_final_log(self):
        self.activity.observe(self.state(['job']))
        state=self.state([],jobStatus='failed');state['logs']='Unable to download manifests\nrefresh_token=private'
        self.activity.observe(state)
        event=self.activity.detail(self.activity.list()[0]['id'])
        self.assertEqual(event['status'],'failed');self.assertNotIn('private',event['logs'])
        self.assertNotIn('logs',self.activity.list()[0])
    def test_actions_store_only_allowed_fields(self):
        self.activity.action('/api/start',200,{'id':526870,'password':'private','headers':{'token':'private'}})
        stored=self.activity.path.read_text()
        self.assertNotIn('private',stored);self.assertEqual(self.activity.list()[0]['status'],'accepted')
        self.assertEqual(len(Activity(self.base).list()),1)
    def test_retention_is_bounded(self):
        for i in range(205):self.activity.action('/api/check',200,{'id':i})
        self.assertEqual(len(self.activity.list()),200)
    def test_restart_idle_does_not_invent_old_sessions(self):
        self.activity.observe(self.state([]));self.assertEqual(self.activity.list(),[])
    def test_managed_native_session_retains_final_log_on_end(self):
        self.activity.observe(self.state(['web-job'],canStop=True))
        end=self.state([]);end['logs']='Prefill complete!\nUp To Date: 12'
        self.activity.observe(end)
        self.assertIn('Prefill complete!',self.activity.detail(self.activity.list()[0]['id'])['logs'])
    def test_external_session_does_not_inherit_unrelated_service_log(self):
        self.activity.observe(self.state(['terminal-job'],canStop=False))
        end=self.state([]);end['logs']='Some unrelated old service log'
        self.activity.observe(end)
        self.assertNotIn('unrelated',self.activity.detail(self.activity.list()[0]['id'])['logs'])
    def test_failure_observed_early_is_not_lost_when_log_tail_advances(self):
        start=self.state(['job'],canStop=False);start['logs']='Unable to download manifests! Skipping app...'
        self.activity.observe(start)
        later=self.state(['job'],canStop=False);later['logs']='Downloading another game'
        self.activity.observe(later);self.activity.observe(self.state([]))
        self.assertEqual(self.activity.list()[0]['status'],'failed')
    def test_log_excerpts_are_bounded_and_redacted(self):
        self.assertEqual(clean_log('password private\nuser@example.com\nSteam Guard code\nOK'),'OK')
        self.assertLessEqual(len(clean_log('X'*20000)),12000)

if __name__=='__main__':unittest.main()
