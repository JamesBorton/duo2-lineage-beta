# SPDX-License-Identifier: Apache-2.0
"""Host-only scripted phone integration. No USB, keys or real subprocesses."""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import installer as app
import verify_package as crypto
import assembly
import stock_layout
app.verify_package, app.assembly, app.stock_layout = crypto, assembly, stock_layout


NAMES = ['boot', 'dtbo', 'odm', 'product', 'system', 'system_ext', 'vbmeta', 'vbmeta_system', 'vendor', 'vendor_boot']


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class UI:
    def __init__(self, phone, cancel=None):
        self.phone, self.cancel, self.logs = phone, cancel, []

    def log(self, text):
        self.logs.append(text)

    def confirm(self, text):
        if self.cancel and self.cancel in text:
            raise app.Stop('Cancelled by synthetic owner')

    def typed(self, text, word):
        self.confirm(text)
        self.phone.consents.append(word)

    def step(self, text):
        self.confirm(text)
        if 'Apply update' in text:
            self.phone.mode = 'sideload'
            if self.phone.expire:
                self.phone.installer.state['preflight_time'] = '2000-01-01T00:00:00+00:00'
        if 'Format data/factory reset' in text:
            self.phone.log += b'Data wipe failed.\n' if self.phone.wipe_fail else b'Data wipe complete.\n'
        if 'additional apps' in text:
            self.phone.mode = 'recovery'

    def choice(self, text, choices):
        if text.startswith('Finish this installed beta'):
            return self.phone.resume_choice
        if text.startswith('Choose your fresh beta layout'):
            return 'workspace' if self.phone.choose_workspace else 'standard'
        return choices[0][0]


class Phone:
    def __init__(self, first=False, slot='a', locked=False):
        self.first, self.source, self.locked = first, slot, locked
        self.mode, self.installed, self.log = 'device', False, b'recovery startup\n'
        self.calls, self.consents = [], []
        self.expire = self.wipe_fail = self.bad_ufs = self.bad_hash = self.bad_signature = False
        self.bad_build = self.fatal = self.transport_fail = self.fail_after_install = False
        self.bad_trust = self.insecure = self.snapshots = self.expire_battery = self.bad_source = False
        self.bad_stock = self.unknown_lock = False
        self.installer = None
        self.workspace = '1'
        self.workspace_active = True
        self.workspace_transition_complete = True
        self.normal_reboots = 0
        self.resume_choice = 'current'
        self.choose_workspace = False
        self.missing_boot_messages = False
        self.fake_capture = False
        self.checkpoint = '1'

    @property
    def target(self):
        return 'b' if self.source == 'a' else 'a'

    def slots(self):
        active = self.target if self.installed else self.source
        states = [{'bootable': True, 'successful': True} for _ in range(2)]
        if self.installed:
            states[0 if self.target == 'a' else 1]['successful'] = False
        return {'slots': 2, 'current': 0 if self.source == 'a' else 1,
                'active': 0 if active == 'a' else 1, 'merge_status': 0, 'slot_state': states}

    def shell(self, args):
        release = self.installer.release
        if args == ['cmd','window','zeta-workspace','status']:return 'enabled=' + ('true' if self.workspace_active else 'false') + ' composition=2 setupComplete=' + ('true' if self.workspace_transition_complete else 'false')
        if args[:1] == ['getprop']:
            new = self.installed and self.mode == 'device'
            values = {'ro.boot.serialno': 'PHONE', 'ro.hardware': 'surfaceduo2',
                      'ro.product.device': 'zeta' if new or self.mode == 'recovery' or not self.first else 'duo2',
                      'ro.build.date.utc': '200' if new else ('10' if self.first and self.mode == 'device' else self.installer.state.get('recovery_build', '100')),
                      'ro.boot.slot_suffix': '_' + (self.target if new else self.source),
                      'sys.boot_completed': '1', 'vold.checkpoint_committed': self.checkpoint, 'ro.adb.secure': '0' if self.insecure else '1', 'ro.adb.secure.recovery': '',
                      'ro.build.version.incremental': 'STOCK', 'init.svc.zeta.bootctrl': 'running'}
            return values[args[1]]
        if args[0] == 'getenforce': return 'Enforcing'
        if args[0] == 'id': return 'uid=0(root)'
        if args[:2] == ['dumpsys', 'battery']: return 'USB powered: true\n  level: 100\n'
        if args[0] == 'settings':
            if args[-1] == 'zeta_workspace_enabled': return self.workspace
            if args[:3] == ['settings', 'put', 'global']:
                self.workspace = args[-1];return ''
            if args[-1] == 'android_id': return '1234567890abcdef'
            return '1'
        if args[:2] == ['pm', 'path']:
            return 'package:/system_ext/priv-app/' + ('Launcher/Launcher.apk' if args[-1].endswith('launcher3') else 'SystemUI/SystemUI.apk')
        if args[0] == 'sha256sum':
            if '/by-name/boot_' in args[-1]: return release['partitions'][0]['sha256'] + '  boot'
            name = ('services' if args[-1].endswith('services.jar') else 'resources' if args[-1].endswith('framework-res.apk')
                    else 'launcher' if 'Launcher' in args[-1] else 'systemui')
            hashes = release['runtime'] if self.installed else release['sources']['100']['runtime']
            return (digest('changed') if self.bad_source and not self.installed else hashes[name]) + '  path'
        if args[0].startswith('head -c'):
            name = re.search('by-name/([a-z_]+)', args[0])[1]
            return release['stock_partitions'][name]['sha256'] + '  -'
        if args[0] == 'cat':
            if args[-1] == '/proc/sys/kernel/random/boot_id': return ('new' if self.normal_reboots <= 1 else 'new-' + str(self.normal_reboots)) if self.installed and self.mode == 'device' else 'ram'
            if args[-1] == app.UFS:
                slot = self.source if self.bad_ufs or not self.installed else self.target
                return '1' if slot == 'a' else '2'
        if args[0].startswith('if [ -r /sys'): return 'UNAVAILABLE'
        if args[:2] == ['timeout', '20s']: return json.dumps(self.slots())
        if args[0] == 'pidof': return {'system_server': '111', 'com.android.systemui': '222', 'com.android.launcher3': '333'}[args[1]]
        if args[:2] == ['cmd', 'window']: return 'enabled=true'
        if args[0] == 'logcat':
            if 'crash' in args: return 'FATAL EXCEPTION test' if self.fatal else ''
            if self.missing_boot_messages: return ''
            return 'Marked slot as booted successfully.\nCheckpoint has been committed.'
        raise AssertionError('Unexpected shell command: ' + repr(args))

    def run(self, args, stdout, stderr, **kwargs):
        args = list(map(str, args)); self.calls.append(args)
        output, error, status = b'', b'', 0
        if args[0] == '/fake/adb':
            assert args[1:5] == ['-P', '5037', '-s', 'PHONE'] or args[1:] == ['-P', '5037', 'devices', '-l']
            cmd = args[5:]
            if args[-2:] == ['devices', '-l']: output = b'List of devices attached\nPHONE device usb:1-1\n'
            elif cmd == ['get-state']: output = self.mode.encode()
            elif cmd == ['reboot', 'bootloader']: self.mode = 'bootloader'
            elif cmd == ['reboot']: self.mode = 'device';self.normal_reboots += 1
            elif cmd[:1] == ['shell']: output = self.shell(cmd[1:]).encode()
            elif cmd[:2] == ['exec-out', 'cat']:
                if cmd[-1] == '/tmp/recovery.log': output = self.log
                else:
                    f = io.BytesIO()
                    with zipfile.ZipFile(f, 'w') as z: z.writestr('beta.x509.pem', '-----BEGIN CERTIFICATE-----\n' + base64.b64encode(b'wrong' if self.bad_trust else b'trusted').decode() + '\n-----END CERTIFICATE-----')
                    output = f.getvalue()
            elif cmd[:1] == ['sideload']:
                assert self.mode == 'sideload'
                if self.transport_fail: status = 1
                else:
                    self.installed = True; self.mode = 'recovery'
                    text = ('whole-file signature verified against RSA key 0\nUpdate package verification took 1.0 s (result 0).\n'
                            'PostinstallRunnerAction with code ErrorCode::kSuccess\nUpdate successfully applied, waiting to reboot.\n'
                            'target_build: ' + ('199' if self.bad_build else '200') + '\n')
                    for part in self.installer.release['partitions']:
                        text += 'Hash of ' + part['name'] + ': ' + (digest('BAD') if self.bad_hash else part['sha256']) + '\n'
                    text += 'Install completed with status ' + ('7' if self.bad_signature else '0') + '.\n'
                    self.log += text.encode()
                    if self.fail_after_install: status = 1
            else: raise AssertionError(args)
        elif args[0] == '/fake/fastboot':
            assert args[1:3] == ['-s', 'PHONE']
            cmd = args[3:]
            if cmd[:1] == ['getvar']:
                values = {'current-slot': self.source, 'serialno': 'PHONE', 'product': 'surfaceduo2',
                          'slot-count': '2', 'unlocked': 'unknown' if self.unknown_lock else ('no' if self.locked else 'yes'),
                          'slot-successful:' + self.source: 'yes', 'slot-unbootable:' + self.source: 'no'}
                error = (cmd[1] + ': ' + values[cmd[1]] + '\n').encode()
            elif cmd[:1] == ['boot']: self.mode = 'recovery'
            elif cmd == ['flashing', 'unlock']:
                assert self.first and 'ERASE' in self.consents
                self.locked = False
            elif cmd == ['reboot']: self.mode = 'device';self.normal_reboots += 1
            else: raise AssertionError('Unreviewed fastboot command: ' + repr(args))
        elif any('preflight-owner-install.py' in a for a in args):
            folder = Path(args[args.index('--output') + 1]);folder.mkdir()
            (folder / 'preflight.json').write_text(json.dumps({'state': 'PASS', 'current_slot': self.source, 'snapshots_none': not self.snapshots}))
        else: raise AssertionError('Unexpected process: ' + repr(args))
        stdout.write(output);stderr.write(error)
        return subprocess.CompletedProcess(args, status)


class PreparedInstaller(app.Installer):
    """Only file assembly/tools discovery are replaced; phone workflow is real."""
    def tools(self, folder=None):
        self.adb, self.fastboot = Path('/fake/adb'), Path('/fake/fastboot')

    def start_boot_capture(self, previous_boot):
        # Workflow fixtures never create a real SDK client/thread.
        if not self.ui.phone.fake_capture:
            return
        name = 'boot-capture-' + str(self.ui.phone.normal_reboots + 1)
        folder = self.session/name;folder.mkdir()
        log = 'Marked slot as booted successfully.\nCheckpoint has been committed.'
        (folder/'boot.log').write_text(log)
        identity = {'ro.boot.serialno':self.serial,'ro.product.device':'zeta',
                    'ro.build.date.utc':self.release['build'],'ro.boot.slot_suffix':'_'+self.state['target_slot']}
        (folder/'capture.json').write_text(json.dumps({'complete':True,'boot_id':'new-'+str(self.ui.phone.normal_reboots+1),
            'identity':identity,'Enforcing':True,'log_sha256':app.sha(folder/'boot.log')}))
        self.save(boot_capture_name=name)

    def public_key(self): return self.kit / 'adbkey.pub'

    def installed_stock_hashes(self):
        return {name: (digest('wrong') if self.ui.phone.bad_stock else info['sha256'])
                for name, info in self.release['stock_partitions'].items()}

    def prepare(self, stock, public_key):
        self.ota.write_bytes(b'OTA')
        self.save('files-prepared', recoveries={build: {'path': str(self.kit / 'boot.img'), 'sha256': digest('BOOT')}
                                               for build in ['100', '200']})


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.shared_lock = patch.object(app, 'phone_lock_root', return_value=self.root/'shared-lock')
        self.shared_lock.start()
        (self.root / 'boot.img').write_bytes(b'BOOT')
        self.release = {'build': '200', 'stock_incremental': 'STOCK', 'ota_sha256': digest('OTA'),
                        'certificate_sha256': digest('trusted'),
                        'runtime': {n: digest('new-' + n) for n in ['services', 'resources', 'systemui', 'launcher']},
                        'sources': {'100': {'recovery': '100', 'runtime': {n: digest('old-' + n) for n in ['services', 'resources', 'systemui', 'launcher']}}},
                        'recoveries': {'100': {}, '200': {}},
                        'partitions': [{'name': n, 'sha256': digest(n), 'size': 4096} for n in NAMES],
                        'stock_partitions': {n: {'sha256': digest('stock-' + n), 'size': 4096} for n in ['vendor', 'odm', 'vendor_boot', 'dtbo']}}

    def tearDown(self): self.shared_lock.stop();self.tmp.cleanup()

    def execute(self, phone=None, cancel=None, mode='update'):
        phone = phone or Phone()
        ui = UI(phone, cancel)
        engine = PreparedInstaller(self.root, self.root / 'work', ui, self.release);phone.installer = engine
        ticks = iter(range(0, 10000, 31))
        with patch.object(app.subprocess, 'run', side_effect=phone.run), patch.object(app.time, 'sleep'), patch.object(app.time, 'monotonic', side_effect=lambda: next(ticks)):
            engine.run(mode, self.root / 'stock.zip', self.root / 'adbkey.pub')
        return engine, phone

    def assert_safe_failure(self, phone, no_reboot=True, **kwargs):
        with self.assertRaises(app.Stop): self.execute(phone, **kwargs)
        if no_reboot:
            self.assertFalse(any(c[0] == '/fake/adb' and c[-1:] == ['reboot'] for c in phone.calls))
        return phone

    def test_manifest_rejects_ambiguous_workspace_policy_types(self):
        for value in ['true', 1, None]:
            with self.subTest(value=value):
                manifest=self.root/'release.json'
                manifest.write_text(json.dumps({'schema':1,'device':'zeta','workspace_default_enabled':value,'files':{}}))
                with patch.object(app,'MANIFEST_SHA256',app.sha(manifest)),self.assertRaisesRegex(app.Stop,'layout policy is invalid'):
                    app.load_release(self.root)

    def test_default_workspace_needs_no_optin_or_extra_reboot(self):
        self.release['workspace_default_enabled']=True
        phone=Phone(first=True);phone.workspace='null'
        with patch.object(UI,'choice',side_effect=AssertionError('No optional layout prompt on default-on target')):
            engine,phone=self.execute(phone,mode='first')
        self.assertEqual(engine.state['phase'],'complete');self.assertTrue(engine.state['workspace_enabled_verified'])
        self.assertEqual(phone.workspace,'null');self.assertEqual(phone.normal_reboots,1)

    def test_default_workspace_requires_actual_completed_layout_transition(self):
        self.release['workspace_default_enabled']=True
        phone=Phone(first=True);phone.workspace='null';phone.workspace_transition_complete=False
        with self.assertRaisesRegex(app.Stop,'expected workspace is not active'):self.execute(phone,mode='first')
        self.assertEqual(phone.workspace,'null');self.assertEqual(phone.normal_reboots,1)
        self.assertNotEqual(phone.installer.state['phase'],'complete')

    def test_default_workspace_preserves_explicit_optout(self):
        self.release['workspace_default_enabled']=True
        phone=Phone(first=True);phone.workspace='0';phone.workspace_active=False
        engine,phone=self.execute(phone,mode='first')
        self.assertEqual(engine.state['phase'],'complete');self.assertEqual(phone.workspace,'0');self.assertEqual(phone.normal_reboots,1)
        self.assertFalse(engine.state['workspace_enabled_verified'])

    def test_inactive_unset_default_stops_without_enabling_or_rebooting(self):
        self.release['workspace_default_enabled']=True
        phone=Phone(first=True);phone.workspace='null';phone.workspace_active=False
        with self.assertRaisesRegex(app.Stop,'expected workspace is not active'):self.execute(phone,mode='first')
        self.assertEqual(phone.workspace,'null');self.assertEqual(phone.normal_reboots,1)
        self.assertNotEqual(phone.installer.state['phase'],'complete')

    def test_missing_startup_logs_stops_without_reinstall(self):
        p=Phone();p.missing_boot_messages=True
        with self.assertRaises(app.Stop):self.execute(p)
        self.assertEqual(p.normal_reboots,1)
        self.assertEqual(sum('sideload' in c for c in p.calls),1)
        self.assertNotEqual(p.installer.state['phase'],'complete')

    def test_resume_workspace_reboot_uses_retained_actual_boot_messages(self):
        p=Phone(first=True);p.workspace='null';p.missing_boot_messages=True
        with self.assertRaises(app.Stop):self.execute(p,mode='first')
        e=p.installer;old_attempt=e.state['validation_attempt'];p.fake_capture=True;p.resume_choice='workspace'
        ticks=iter(range(0,10000,31))
        with patch.object(app.subprocess,'run',side_effect=p.run),patch.object(app.verify_package,'verify'),patch.object(app.time,'sleep'),patch.object(app.time,'monotonic',side_effect=lambda:next(ticks)):
            e.check_session(e.session/'state.json')
        self.assertEqual(e.state['phase'],'complete');self.assertEqual(p.workspace,'1')
        self.assertEqual(p.normal_reboots,2);self.assertEqual(sum('sideload' in c for c in p.calls),1)
        self.assertTrue((Path(old_attempt)/'stability.json').exists())
        self.assertNotEqual(old_attempt,e.state['validation_attempt'])
        before=len(p.calls)
        with self.assertRaises(app.Stop):e.validation_reboot(True)
        self.assertEqual(before,len(p.calls))

    def test_update_workspace_optin_does_not_compare_against_old_layout(self):
        p=Phone();p.workspace='0';p.missing_boot_messages=True
        with self.assertRaises(app.Stop):self.execute(p)
        e=p.installer;p.fake_capture=True;p.resume_choice='workspace';ticks=iter(range(0,10000,31))
        with patch.object(app.subprocess,'run',side_effect=p.run),patch.object(app.verify_package,'verify'),patch.object(app.time,'sleep'),patch.object(app.time,'monotonic',side_effect=lambda:next(ticks)):
            e.check_session(e.session/'state.json')
        self.assertEqual(e.state['phase'],'complete');self.assertEqual(p.workspace,'1')
        self.assertEqual(e.state['workspace'],'0');self.assertEqual(e.state['validation_workspace'],'1')
        self.assertEqual(sum('sideload' in c for c in p.calls),1)

    def test_pending_checkpoint_blocks_validation_reboot(self):
        e,p=self.execute();p.checkpoint='0'
        before=p.normal_reboots
        with patch.object(app.subprocess,'run',side_effect=p.run),self.assertRaises(app.Stop):e.validation_reboot()
        self.assertEqual(p.normal_reboots,before)

    def test_unsupported_mode_cannot_fall_into_first_install(self):
        p=Phone(first=True)
        with self.assertRaises(app.Stop):self.execute(p,mode='unknown')
        self.assertEqual(p.calls,[])

    def test_update_a_to_b(self):
        e, p = self.execute(); self.assertEqual(e.state['phase'], 'complete');self.assertEqual(e.state['target_slot'], 'b')
        self.assertFalse(p.consents);self.assertEqual(sum('sideload' in c for c in p.calls), 1)

    def test_update_b_to_a(self):
        e, _ = self.execute(Phone(slot='b'));self.assertEqual(e.state['target_slot'], 'a')

    def test_cancel_before_any_mutation(self):
        p = self.assert_safe_failure(Phone(), cancel='Ready to')
        self.assertFalse(any('reboot' in c or 'boot' in c or 'sideload' in c for c in p.calls))

    def test_expired_menu_check_does_not_send(self):
        p = Phone();p.expire=True;self.assert_safe_failure(p);self.assertFalse(any('sideload' in c for c in p.calls))

    def test_expiration_during_final_package_hash_does_not_send(self):
        p=Phone();real_sha=app.sha
        def delayed_sha(path):
            if p.installer and Path(path)==p.installer.ota and p.mode=='sideload':
                p.installer.state['preflight_time']='2000-01-01T00:00:00+00:00'
            return real_sha(path)
        with patch.object(app,'sha',side_effect=delayed_sha):self.assert_safe_failure(p)
        self.assertFalse(any('sideload' in c for c in p.calls))

    def test_bad_hash_does_not_reboot(self):
        p=Phone();p.bad_hash=True;self.assert_safe_failure(p)

    def test_signature_failure_does_not_reboot(self):
        p=Phone();p.bad_signature=True;self.assert_safe_failure(p)

    def test_wrong_target_does_not_reboot(self):
        p=Phone();p.bad_build=True;self.assert_safe_failure(p)

    def test_wrong_ufs_does_not_reboot(self):
        p=Phone();p.bad_ufs=True;self.assert_safe_failure(p)

    def test_transport_failure_never_reboots(self):
        p=Phone();p.transport_fail=True;self.assert_safe_failure(p)

    def test_fatal_crash_is_not_success(self):
        p=Phone();p.fatal=True;self.assert_safe_failure(p, no_reboot=False)
        self.assertNotEqual(p.installer.state['phase'], 'complete')

    def test_first_install_requires_explicit_erase_and_format(self):
        e,p=self.execute(Phone(first=True),mode='first');self.assertEqual(e.state['phase'],'complete')
        self.assertEqual(p.consents,['ERASE']);self.assertTrue(e.state['format_verified'])

    def test_first_install_locked_bootloader_unlock_consent(self):
        e,p=self.execute(Phone(first=True,locked=True),mode='first');self.assertEqual(e.state['phase'],'complete')
        self.assertEqual(p.consents,['ERASE','ERASE'])

    def test_first_format_failure_does_not_send(self):
        p=Phone(first=True);p.wipe_fail=True;self.assert_safe_failure(p,mode='first')
        self.assertFalse(any('sideload' in c for c in p.calls))

    def test_wrong_stock_bytes_never_offer_format(self):
        p=Phone(first=True);p.bad_stock=True;self.assert_safe_failure(p,mode='first')
        self.assertFalse(p.consents);self.assertFalse(any('sideload' in c for c in p.calls))

    def test_unknown_lock_state_never_requests_unlock(self):
        p=Phone(first=True);p.unknown_lock=True;self.assert_safe_failure(p,mode='first')
        self.assertFalse(p.consents);self.assertFalse(any('unlock' in c for c in p.calls))

    def test_update_never_unlocks_locked_bootloader(self):
        p=self.assert_safe_failure(Phone(locked=True));self.assertFalse(any('unlock' in c for c in p.calls))

    def test_wrong_recovery_signer_never_sends(self):
        p=Phone();p.bad_trust=True;self.assert_safe_failure(p)
        self.assertFalse(any('sideload' in c for c in p.calls))

    def test_insecure_recovery_never_sends(self):
        p=Phone();p.insecure=True;self.assert_safe_failure(p)
        self.assertFalse(any('sideload' in c for c in p.calls))

    def test_snapshot_records_block_transfer(self):
        p=Phone();p.snapshots=True;self.assert_safe_failure(p)
        self.assertFalse(any('sideload' in c for c in p.calls))

    def test_changed_source_code_blocks_all_phone_mutation(self):
        p=Phone();p.bad_source=True;self.assert_safe_failure(p)
        self.assertFalse(any('reboot' in c or 'boot' in c or 'sideload' in c for c in p.calls))

    def test_first_install_cancel_never_formats_or_sends(self):
        p=self.assert_safe_failure(Phone(first=True),mode='first',cancel='FIRST INSTALLATION')
        self.assertNotIn(b'Data wipe complete.',p.log);self.assertFalse(any('sideload' in c for c in p.calls))

    def test_first_install_does_not_erase_a_compatible_beta(self):
        p=self.assert_safe_failure(Phone(),mode='first')
        self.assertFalse(p.consents);self.assertFalse(any('reboot' in c for c in p.calls))

    def test_resume_failed_install_never_starts_second_sender(self):
        p=Phone();p.transport_fail=True;self.assert_safe_failure(p)
        e=p.installer;p.mode='recovery';count=len([c for c in p.calls if 'sideload' in c])
        with patch.object(app.subprocess,'run',side_effect=p.run),patch.object(app.verify_package,'verify'),self.assertRaises(app.Stop):
            e.check_session(e.session/'state.json')
        self.assertEqual(count,len([c for c in p.calls if 'sideload' in c]))

    def test_changed_session_slot_is_rejected_before_any_phone_command(self):
        e,p=self.execute();path=e.session/'state.json';state=json.loads(path.read_text())
        state['target_slot']='b; reboot';path.write_text(json.dumps(state));count=len(p.calls)
        with patch.object(app.subprocess,'run',side_effect=p.run),self.assertRaises(app.Stop):e.check_session(path)
        self.assertEqual(count,len(p.calls))

    def test_second_phone_cannot_replace_original(self):
        e=PreparedInstaller(self.root,self.root/'newwork',UI(Phone()),self.release)
        e.begin('update');e.tools();e.serial='ORIGINAL'
        phone=Phone();phone.installer=e
        with patch.object(app.subprocess,'run',side_effect=phone.run),self.assertRaises(app.Stop):e.discover()

    def test_cancelled_erase_does_not_unlock(self):
        p=self.assert_safe_failure(Phone(first=True,locked=True),mode='first',cancel='Unlocking the bootloader')
        self.assertFalse(any('unlock' in c for c in p.calls))

    def test_preparation_sends_no_device_commands(self):
        e,p=self.execute(mode='prepare');self.assertEqual(p.calls,[]);self.assertEqual(e.state['phase'],'preparation-complete-no-device-commands')

    def test_resume_after_transport_error_proves_recovery_without_resending(self):
        p=Phone();p.fail_after_install=True;self.assert_safe_failure(p)
        e=p.installer;state=e.session/'state.json';original=len([c for c in p.calls if 'sideload' in c])
        p.fail_after_install=False;ticks=iter(range(0,10000,31))
        with patch.object(app.subprocess,'run',side_effect=p.run), patch.object(app.verify_package,'verify'), patch.object(app.time,'sleep'), patch.object(app.time,'monotonic',side_effect=lambda:next(ticks)):
            e.check_session(state)
        self.assertEqual(e.state['phase'],'complete');self.assertEqual(original,len([c for c in p.calls if 'sideload' in c]))

    def test_work_folder_cannot_be_existing_personal_folder(self):
        with self.assertRaises(app.Stop):PreparedInstaller(self.root,self.root,UI(Phone()),self.release)

    def test_unsafe_kit_path_rejected(self):
        with self.assertRaises(app.Stop):app.safe_child(self.root,'../outside')

    def test_double_installer_lock_rejected(self):
        work=self.root/'lock';work.mkdir()
        with app.PhoneLock(work),self.assertRaises(app.Stop):
            with app.PhoneLock(work):pass

    def test_different_work_folders_cannot_run_two_phone_operations(self):
        phone=Phone()
        with app.PhoneLock(app.phone_lock_root()),self.assertRaises(app.Stop):self.execute(phone)
        self.assertEqual(phone.calls,[])



class BootstrapSecurityTests(unittest.TestCase):
    def test_tampered_module_stops_before_any_code_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); marker = root / 'executed'
            path = root / 'fixture.py'; path.write_text('value = 7\n')
            release = {'files': {'fixture.py': app.sha(path)}}
            path.write_text('from pathlib import Path; Path(' + repr(str(marker)) + ').touch()\n')
            with self.assertRaises(app.Stop):
                app.verified_module(root, release, 'audit_fixture', 'fixture.py')
            self.assertFalse(marker.exists())

    def test_matching_source_loaded_without_import_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'fixture.py'
            path.write_text('value = 7\n')
            release = {'files': {'fixture.py': app.sha(path)}}
            (root / '__pycache__').mkdir()
            (root / '__pycache__/fixture.cpython-314.pyc').write_bytes(b'untrusted cache')
            result = app.verified_module(root, release, 'audit_fixture', 'fixture.py')
            self.assertEqual(result.value, 7)
            sys.modules.pop('audit_fixture', None)

    def test_unpinned_module_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'extra.py').write_text('raise RuntimeError("must not run")')
            with self.assertRaises(app.Stop):
                app.verified_module(root, {'files': {}}, 'audit_fixture', 'extra.py')

    def test_real_isolated_bootstrap_rejects_tamper_and_ignores_shadow_modules(self):
        import os
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); marker = root/'executed'
            body = Path(app.__file__).read_text()
            for name in ('assembly.py','stock_layout.py','verify_package.py','installer_ui.py'):
                (root/name).write_text('raise SystemExit("verified fixture reached")\n' if name=='assembly.py' else '')
            (root/'ota.x509.pem').write_text('-----BEGIN CERTIFICATE-----\nZg==\n-----END CERTIFICATE-----\n')
            release = {'schema':1,'device':'zeta','certificate_sha256':hashlib.sha256(b'f').hexdigest(),
                       'files':{p.name:app.sha(p) for p in root.iterdir() if p.is_file()}}
            (root/'release.json').write_text(json.dumps(release))
            (root/'installer.py').write_text(body.replace('STAMPED_BY_MAINTAINER_EXPORT', app.sha(root/'release.json')))
            evil = 'from pathlib import Path; Path(' + repr(str(marker)) + ').touch()\n'
            # Unlisted local modules and Python environment hooks cannot run first.
            (root/'zipfile.py').write_text(evil)
            injection = root/'injection';injection.mkdir();(injection/'sitecustomize.py').write_text(evil)
            env=dict(os.environ, PYTHONPATH=str(injection))
            result=subprocess.run([sys.executable,'-I',str(root/'installer.py'),'--console'],
                                  cwd=root,env=env,capture_output=True,text=True,timeout=15)
            self.assertIn('verified fixture reached',result.stderr)
            self.assertFalse(marker.exists())
            (root/'assembly.py').write_text(evil)
            result=subprocess.run([sys.executable,'-I',str(root/'installer.py'),'--console'],
                                  cwd=root,env=env,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('missing or changed',result.stderr)
            self.assertFalse(marker.exists())

    def test_developer_environment_hooks_removed(self):
        value = app.helper_environment({'PATH': '/official/tools', 'HOME': '/owner',
                 'PYTHONPATH': '/evil', 'PYTHONSTARTUP': '/evil/startup',
                 'AVB_INVOCATION_LOGFILE': '/unrequested/write',
                 'ANDROID_SECURE_STORAGE_CMD': 'arbitrary command', 'TMP__KEY_FILE_NAME': '/secret'})
        self.assertEqual(value, {'PATH': '/official/tools', 'HOME': '/owner'})

    @unittest.skipIf(sys.platform == 'win32', 'POSIX privilege guard')
    def test_root_execution_rejected(self):
        with patch.object(app.os, 'geteuid', return_value=0):
            with self.assertRaises(app.Stop): app.require_normal_user()

    def test_launchers_and_child_python_use_isolation(self):
        root = Path(__file__).resolve().parent
        self.assertIn('python3 -I', (root/'Install.sh').read_text())
        self.assertIn('py -3 -I', (root/'Install.cmd').read_text())
        self.assertIn('python -I', (root/'Install.cmd').read_text())

if __name__ == '__main__': unittest.main()
