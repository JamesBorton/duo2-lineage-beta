# SPDX-License-Identifier: Apache-2.0
"""Real local fake-SDK capture plus adversarial retained-evidence tests. No USB."""
import hashlib,json,os,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import installer as app

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.engine=app.Installer(self.root,self.root/'work',None,{'build':'200'})
        self.engine.begin('first');self.engine.serial='PHONE';self.engine.state['target_slot']='b'
        self.name='boot-capture-123';self.folder=self.engine.session/self.name;self.folder.mkdir()
        self.engine.state['boot_capture_name']=self.name
        self.text='Marked slot as booted successfully.\nCheckpoint has been committed.'
        (self.folder/'boot.log').write_text(self.text)
        self.report={'complete':True,'boot_id':'new','Enforcing':True,'log_sha256':app.sha(self.folder/'boot.log'),
                     'identity':{'ro.boot.serialno':'PHONE','ro.product.device':'zeta','ro.build.date.utc':'200','ro.boot.slot_suffix':'_b'}}
        self.write()
    def write(self):(self.folder/'capture.json').write_text(json.dumps(self.report))
    def tearDown(self):self.tmp.cleanup()
    def test_prior_commit_is_bound_to_successful_reboot_order(self):
        self.engine.state['validation_reboot_requested']=True
        read=self.engine.session/'0010-checkpoint-before-validation-reboot.stdout';read.write_text('1\n')
        read.with_suffix('.exit').write_text('0')
        reboot=self.engine.session/'0020-normal-validation-reboot.exit';reboot.write_text('0')
        self.assertTrue(self.engine.prior_committed_validation_context())
        read.write_text('0\n')
        later=self.engine.session/'0030-checkpoint-before-validation-reboot.stdout';later.write_text('1\n');later.with_suffix('.exit').write_text('0')
        self.assertFalse(self.engine.prior_committed_validation_context())
        read.write_text('1\n');reboot.write_text('1')
        self.assertFalse(self.engine.prior_committed_validation_context())
    def test_ambiguous_reboots_cannot_prove_prior_commit(self):
        self.engine.state['validation_reboot_requested']=True
        for number in (20,30):(self.engine.session/(str(number)+'-normal-validation-reboot.exit')).write_text('0')
        self.assertFalse(self.engine.prior_committed_validation_context())

    def test_same_boot_verified_capture(self):self.assertEqual(self.engine.captured_boot_text('new'),self.text)
    def test_old_boot_never_satisfies_evidence(self):self.assertEqual(self.engine.captured_boot_text('different'),'')
    def test_incomplete_capture_not_accepted(self):
        self.report['complete']=False;self.write();self.assertEqual(self.engine.captured_boot_text('new'),'')
    def test_changed_log_rejected(self):
        (self.folder/'boot.log').write_text(self.text+' altered')
        with self.assertRaises(app.Stop):self.engine.captured_boot_text('new')
    def test_wrong_serial_build_slot_or_enforcement_rejected(self):
        for key in self.report['identity']:
            old=self.report['identity'][key];self.report['identity'][key]='wrong';self.write()
            with self.subTest(key=key),self.assertRaises(app.Stop):self.engine.captured_boot_text('new')
            self.report['identity'][key]=old
        self.report['Enforcing']=False;self.write()
        with self.assertRaises(app.Stop):self.engine.captured_boot_text('new')
    def test_untrusted_capture_path_rejected(self):
        self.engine.state['boot_capture_name']='../capture'
        with self.assertRaises(app.Stop):self.engine.captured_boot_text('new')
    @unittest.skipIf(os.name=='nt','POSIX symlink test')
    def test_log_symlink_cannot_escape_capture_folder(self):
        log=self.folder/'boot.log';log.unlink();outside=self.root/'outside.log';outside.write_text(self.text)
        log.symlink_to(outside)
        with self.assertRaises(app.Stop):self.engine.captured_boot_text('new')
    @unittest.skipIf(os.name=='nt','Local POSIX fake executable; Windows remains unqualified')
    def test_real_capture_process_and_clean_shutdown(self):
        executable=self.root/'fake-adb'
        expected=self.report['identity']
        executable.write_text('#!'+sys.executable+'\nimport sys,time\na=sys.argv[5:]\nvalues='+repr(expected)+'''\nif a==['get-state']: print('device')
elif a[:2]==['shell','getprop']: print(values.get(a[2],''))
elif a[:2]==['shell','cat']: print('new')
elif a==['shell','getenforce']: print('Enforcing')
elif a[:1]==['logcat']:
 print('Marked slot as booted successfully.\\nCheckpoint has been committed.',flush=True)
 time.sleep(30)
else: raise SystemExit(1)
''')
        executable.chmod(0o700)
        folder=self.root/'actual-capture';cap=app.BootCapture(folder,executable,'PHONE',os.environ.copy(),expected,'old')
        try:
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if (folder/'boot.log').exists() and (folder/'boot.log').stat().st_size:break
                time.sleep(.02)
        finally:cap.close()
        self.assertFalse(cap.thread.is_alive());self.assertIsNotNone(cap.child);self.assertIsNotNone(cap.child.poll())
        facts=json.loads((folder/'capture.json').read_text());self.assertTrue(facts['complete']);self.assertEqual(facts['boot_id'],'new')
        self.assertEqual(facts['log_sha256'],app.sha(folder/'boot.log'))

class CheckpointSemanticsTests(unittest.TestCase):
    marked='Checkpoint: Marked slot as booted successfully.\n'
    inactive='Checkpoint: NOT COMMITTING CHECKPOINT BECAUSE isCheckpointing == false\n'
    def test_actual_commit(self):
        result=app.boot_evidence(self.marked+'Checkpoint has been committed.')
        self.assertTrue(result['checkpoint_committed_this_boot'])
    def test_explicit_inactive_only_after_proven_validation_context(self):
        result=app.boot_evidence(self.marked+self.inactive,True)
        self.assertFalse(result['checkpoint_committed_this_boot'])
        self.assertEqual(result['checkpoint_status'],'inactive_after_committed_validation_reboot')
    def test_no_absence_or_property_only_fallback(self):
        for text,context in [(self.marked,True),(self.marked+self.inactive,False),(self.inactive,True),
                             (self.marked+'NOT COMMITTING CHECKPOINT BECAUSE persist.vold.dont_commit_checkpoint IS 1',True),
                             ('Checkpoint has been committed.',True)]:
            with self.subTest(text=text,context=context),self.assertRaises(app.Stop):app.boot_evidence(text,context)
