#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guided Surface Duo 2 installer. No device action on import or preparation.

The maintainer exporter stamps MANIFEST_SHA256. There are deliberately no
skip-verification, forced-slot, unauthenticated-ADB or arbitrary-flash options.
"""
# Isolate before importing any non-frozen stdlib or kit module. Launchers also
# supply -I so Python startup ignores PYTHONPATH and user-site hooks from outset.
import os
import sys
if __name__ == '__main__' and not sys.flags.isolated:
    os.execv(sys.executable, [sys.executable, '-I', os.path.abspath(__file__), *sys.argv[1:]])

import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import types
import threading
import zipfile


MANIFEST_SHA256 = 'STAMPED_BY_MAINTAINER_EXPORT'
UFS = '/sys/bus/platform/devices/1d84000.ufshc/attributes/boot_lun_enabled'
RUNTIME = {'services': '/system/framework/services.jar',
           'resources': '/system/framework/framework-res.apk'}


class Stop(Exception):
    """A safe stop, shown without a traceback to the owner."""


def need(ok, message):
    if not ok:
        raise Stop(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def age(value):
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(value)).total_seconds()


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def safe_child(root, name):
    path = (root / name).resolve()
    need(path.is_relative_to(root.resolve()) and path != root.resolve(), 'The kit contains an unsafe file path.')
    return path


def certificate_der(path):
    text = Path(path).read_text(encoding='ascii')
    return base64.b64decode(''.join(text.split('-----BEGIN CERTIFICATE-----')[1]
                                  .split('-----END CERTIFICATE-----')[0].split()), validate=True)


def load_release(root):
    path = root / 'release.json'
    need(path.is_file() and sha(path) == MANIFEST_SHA256,
         'This kit is incomplete or changed. Extract a fresh verified installer kit; do not mix releases.')
    release = json.loads(path.read_text())
    need(release['schema'] == 1 and release['device'] == 'zeta', 'This installer kit is not supported.')
    need(type(release.get('workspace_default_enabled', False)) is bool, 'The release layout policy is invalid.')
    for name, digest in release['files'].items():
        file = safe_child(root, name)
        need(file.is_file() and sha(file) == digest, 'A kit file is missing or changed: ' + name)
    need(hashlib.sha256(certificate_der(root / 'ota.x509.pem')).hexdigest() == release['certificate_sha256'],
         'The beta signing certificate is wrong.')
    return release


def verified_module(root, release, name, filename):
    """Compile exactly the verified source bytes, never an unchecked .pyc/import."""
    path = safe_child(root, filename)
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == release['files'].get(filename),
         'An executable helper changed before loading: ' + filename)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ''
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def load_dependencies(root, release):
    global assembly, verify_package, stock_layout
    assembly = verified_module(root, release, 'assembly', 'assembly.py')
    stock_layout = verified_module(root, release, 'stock_layout', 'stock_layout.py')
    verify_package = verified_module(root, release, 'verify_package', 'verify_package.py')


def require_normal_user():
    if os.name == 'nt':
        import ctypes
        need(not ctypes.windll.shell32.IsUserAnAdmin(),
             'Run the installer as your normal user, not as administrator.')
    else:
        need(os.geteuid() != 0, 'Run the installer as your normal user, not as root.')


def helper_environment(environment):
    # avbtool supports optional developer hooks/log files; this fixed owner flow
    # must not inherit those hooks or Python injection into child interpreters.
    return {k: v for k, v in environment.items()
            if not k.upper().startswith('PYTHON') and
            k.upper() not in ('AVB_INVOCATION_LOGFILE', 'ANDROID_SECURE_STORAGE_CMD', 'TMP__KEY_FILE_NAME')}


def boot_evidence(checkpoint, committed_validation_context=False):
    marked = bool(re.search(r'Mark(?:ing|ed).*boot.*successful', checkpoint, re.I))
    committed = bool(re.search(r'Checkpoint (?:has been )?committed', checkpoint, re.I))
    inactive = 'NOT COMMITTING CHECKPOINT BECAUSE isCheckpointing == false' in checkpoint
    need(marked and (committed or (committed_validation_context and inactive)),
         'Startup evidence is incomplete. Do not reinstall. Use Check last installation to inspect this boot or request one validation reboot if available.')
    return {'automatic_boot_success': True, 'checkpoint_committed_this_boot': committed,
            'checkpoint_status': 'committed' if committed else 'inactive_after_committed_validation_reboot'}


class Console:
    def log(self, text):
        print(text, flush=True)

    def choice(self, text, choices):
        print('\n' + text)
        for i, (_, label) in enumerate(choices, 1):
            print(f'  {i}. {label}')
        answer = input('Choose a number (Enter cancels): ').strip()
        need(answer.isdigit() and 1 <= int(answer) <= len(choices), 'Cancelled. No further steps were taken.')
        return choices[int(answer) - 1][0]

    def confirm(self, text):
        need(input('\n' + text + '\nContinue? [y/N] ').strip().lower() in ('y', 'yes'),
             'Cancelled. No further steps were taken.')

    def typed(self, text, word):
        need(input('\n' + text + '\nType ' + word + ' to continue: ').strip() == word,
             'Cancelled. No erase/unlock request was sent.')

    def file(self, text, default=''):
        value = input('\n' + text + (f' [{default}]' if default else '') + ': ').strip().strip('"') or default
        need(value, 'Cancelled.')
        return Path(value).expanduser().resolve()

    def step(self, text):
        self.confirm(text)


class PhoneLock:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = root / 'installer.lock'

    def __enter__(self):
        self.f = self.path.open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.f.seek(0)
                self.f.write(b'0')
                self.f.flush()
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            raise Stop('Another installer is running. Finish it first; do not start a second copy.')
        return self

    def __exit__(self, *args):
        self.f.close()

class BootCapture:
    """Read-only early boot log stream; never changes a phone or ADB auth."""
    def __init__(self, folder, adb, serial, env, expected, previous_boot):
        self.folder, self.base = folder, [str(adb), '-P', '5037', '-s', serial]
        self.env, self.expected, self.previous_boot = env, expected, previous_boot
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.child = None
        self.folder.mkdir(mode=0o700)
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def query(self, *args):
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        result = subprocess.run(self.base + list(args), env=self.env, capture_output=True,
                                timeout=5, **flags)
        return result.stdout.decode(errors='replace').strip() if result.returncode == 0 else ''

    def worker(self):
        facts = {'complete': False, 'identity': self.expected}
        try:
            deadline = time.monotonic() + 300
            while not self.stop.is_set() and time.monotonic() < deadline:
                try:
                    if self.query('get-state') == 'device':
                        boot = self.query('shell', 'cat', '/proc/sys/kernel/random/boot_id')
                        if boot and boot != self.previous_boot and all(
                                self.query('shell', 'getprop', k) == v for k, v in self.expected.items()) and \
                                self.query('shell', 'getenforce') == 'Enforcing':
                            facts.update(boot_id=boot, started=now(), Enforcing=True)
                            with (self.folder / 'boot.log').open('wb') as out, (self.folder / 'stderr.log').open('wb') as err:
                                with self.lock:
                                    if self.stop.is_set():
                                        break
                                    flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                                    self.child = subprocess.Popen(self.base + ['logcat', '-b', 'all', '-v', 'threadtime',
                                        '-s', 'vold:V', 'Checkpoint:V', 'bootctrl:V', 'bootcontrolhal:V', 'zeta.bootctrl:V'],
                                        env=self.env, stdout=out, stderr=err, **flags)
                                self.child.wait()
                            facts.update(complete=True, log_sha256=sha(self.folder / 'boot.log'))
                            break
                except subprocess.TimeoutExpired:
                    pass
                self.stop.wait(.25)
        except Exception as error:
            facts['error'] = str(error)
        finally:
            facts['ended'] = now()
            (self.folder / 'capture.json').write_text(json.dumps(facts, indent=2) + '\n')

    def close(self):
        self.stop.set()
        with self.lock:
            if self.child is not None and self.child.poll() is None:
                self.child.terminate()  # Local read-only client only; never kill-server.
                try:
                    self.child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=5)
        self.thread.join(timeout=8)
        need(not self.thread.is_alive(), 'The local boot-log capture did not close. Keep the logs and use Help.')


class Installer:
    def __init__(self, kit, work, ui, release=None):
        self.kit, self.work, self.ui = kit.resolve(), work.resolve(), ui
        self.release = release if release is not None else load_release(self.kit)
        # Keep personalized images, keys and phone evidence out of source checkouts.
        need(not any((p / '.git').exists() for p in [self.work, *self.work.parents]),
             'Choose a working folder outside a Git/source-code checkout.')
        need(not self.work.exists() or not any(self.work.iterdir()) or
             (self.work / '.duo2-installer-work').is_file(),
             'Choose a new, empty working folder dedicated to this installer.')
        self.work.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.work.chmod(0o700)
        (self.work / '.duo2-installer-work').touch(exist_ok=True)
        self.serial = None
        self.adb = self.fastboot = None
        self.session = None
        self.counter = 0
        self.capture = None
        self.env = helper_environment(os.environ)
        self.env.pop('ADB_SERVER_SOCKET', None)
        self.env['ANDROID_ADB_SERVER_PORT'] = '5037'
        self.ota = self.work / ('installer-' + self.release['build'] + '.zip')

    def start_boot_capture(self, previous_boot):
        self.close_capture()
        name = 'boot-capture-' + str(time.time_ns())
        self.save(boot_capture_name=name)
        expected = {'ro.boot.serialno': self.serial, 'ro.product.device': 'zeta',
                    'ro.build.date.utc': self.release['build'], 'ro.boot.slot_suffix': '_' + self.state['target_slot']}
        self.capture = BootCapture(self.session / name, self.adb, self.serial, self.env, expected, previous_boot)

    def close_capture(self):
        if self.capture is not None:
            self.capture.close()
            self.capture = None

    def captured_boot_text(self, boot):
        name = self.state.get('boot_capture_name')
        if not name:
            return ''
        need(re.fullmatch(r'boot-capture-[0-9]+', name), 'Unexpected boot capture path.')
        folder = safe_child(self.session, name)
        path = safe_child(folder, 'capture.json')
        if not path.is_file():
            return ''
        report = json.loads(path.read_text())
        if not report.get('complete') or report.get('boot_id') != boot:
            return ''
        expected = {'ro.boot.serialno': self.serial, 'ro.product.device': 'zeta',
                    'ro.build.date.utc': self.release['build'], 'ro.boot.slot_suffix': '_' + self.state['target_slot']}
        need(report.get('identity') == expected and report.get('Enforcing') is True and
             sha(safe_child(folder, 'boot.log')) == report.get('log_sha256'), 'Retained boot evidence changed or has the wrong identity.')
        return safe_child(folder, 'boot.log').read_text(errors='replace')

    def prior_committed_validation_context(self):
        if not self.state.get('validation_reboot_requested'):
            return False
        # Bind the retained property read to the one actual normal-reboot command
        # by command order. This supports v10 sessions without editing evidence.
        def number(path):
            prefix = path.name.split('-', 1)[0]
            return int(prefix) if prefix.isdigit() else -1
        reboots = list(self.session.glob('*-normal-validation-reboot.exit'))
        if len(reboots) != 1 or reboots[0].read_text().strip() != '0':
            return False
        reads = [p for p in self.session.glob('*-checkpoint-before-validation-reboot.stdout')
                 if 0 <= number(p) < number(reboots[0])]
        if not reads:
            return False
        source = max(reads, key=number)
        if source.read_text().strip() != '1' or source.with_suffix('.exit').read_text().strip() != '0':
            return False
        self.state['previous_checkpoint_evidence'] = source.name
        return True

    def validation_reboot(self, enable_workspace=False):
        need(not self.state.get('validation_reboot_requested'),
             'A validation reboot was already requested. Check this boot or use Help; do not repeat it automatically.')
        need(self.state.get('actual_install_status') == 0 and self.state.get('all_ten_installed_hashes_match') and
             self.state.get('recovery_signature_result') == 0, 'Recovery installation evidence is missing; no validation reboot.')
        boot = self.normal_identity()
        need(self.shell('checkpoint-before-validation-reboot', 'getprop', 'vold.checkpoint_committed') == '1',
             'Android has not committed its checkpoint. Keep the phone running and use Help; no reboot requested.')
        need(not re.search(r'FATAL EXCEPTION|Fatal signal|Abort message',
             self.shell('crash-before-validation-reboot', 'logcat', '-b', 'crash', '-d')), 'A fatal crash needs investigation before reboot.')
        android_id = self.shell('validation-userdata-before', 'settings', '--user', '0', 'get', 'secure', 'android_id')
        need(re.fullmatch('[0-9a-fA-F]{16}', android_id), 'Unlock Android before validation.')
        workspace = self.shell('validation-workspace-before', 'settings', 'get', 'global', 'zeta_workspace_enabled')
        self.save('validation-reboot-requested', validation_reboot_requested=True, validation_previous_boot_id=boot,
                  validation_android_id_sha256=hashlib.sha256(android_id.encode()).hexdigest(),
                  validation_workspace='1' if enable_workspace else workspace,
                  workspace_opt_in_consent=enable_workspace, workspace_choice_done=True)
        if enable_workspace:
            self.shell('owner-enable-workspace', 'settings', 'put', 'global', 'zeta_workspace_enabled', '1')
            need(self.shell('workspace-readback', 'settings', 'get', 'global', 'zeta_workspace_enabled') == '1',
                 'Workspace setting did not apply. No reboot requested.')
        self.start_boot_capture(boot)
        self.adb_call('normal-validation-reboot', 'reboot')
        self.ui.step('One normal validation reboot was requested, without erasing or reinstalling. Unlock with your PIN privately, keep USB connected, and continue here.')
        self.wait('device', 300)
        self.validate_normal()

    def verify_default_workspace(self):
        if self.release.get('workspace_default_enabled') is not True:
            return
        setting = self.shell('default-workspace-setting', 'settings', 'get', 'global', 'zeta_workspace_enabled')
        need(setting in ('null', '0', '1'), 'The workspace preference is invalid. Keep your logs and use Help.')
        if setting != '0':
            status = self.shell('default-workspace-status', 'cmd', 'window', 'zeta-workspace', 'status')
            need(re.match(r'^enabled=true(?:\s|$)', status) and
                 re.search(r'(?:^|\s)setupComplete=true(?:\s|$)', status),
                 'The expected workspace is not active. Keep your logs and use Help; no setting or extra reboot was applied.')
        return setting

    def first_install_preferences(self):
        if self.state['mode'] != 'first' or self.state.get('workspace_choice_done'):
            return
        if self.release.get('workspace_default_enabled') is True:
            setting = self.verify_default_workspace()
            self.save(workspace_choice_done=True, workspace_policy_verified=True,
                      workspace_enabled_verified=setting != '0', workspace_preference=setting)
            return
        if self.shell('fresh-workspace-choice', 'settings', 'get', 'global', 'zeta_workspace_enabled') == '1':
            self.save(workspace_choice_done=True)
            return
        choice = self.ui.choice('Choose your fresh beta layout. Independent workspace needs one normal reboot; no erase or reinstall.',
                 [('workspace', 'Enable independent left/right workspace and reboot once'),
                  ('standard', 'Keep the standard layout (no extra reboot)')])
        if choice == 'workspace':
            self.validation_reboot(enable_workspace=True)
        else:
            need(choice == 'standard', 'Cancelled; the installed beta is unchanged.')
            self.save(workspace_choice_done=True)

    def finished_message(self):
        self.ui.log('Finished. The beta is installed and automatic checks passed. Please check both screens/touch, typing and closing/reopening. Keep your local session folder for support.')

    def begin(self, mode):
        self.session = self.work / ('session-' + time.strftime('%Y%m%d-%H%M%S') + '-' + os.urandom(3).hex())
        self.session.mkdir(mode=0o700)
        self.state = {'mode': mode, 'target_build': self.release['build'], 'created': now(), 'phase': 'starting'}
        self.save()

    def save(self, phase=None, **facts):
        if phase:
            self.state['phase'] = phase
        self.state.update(facts)
        self.state['updated'] = now()
        target = self.session / 'state.json'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, indent=2) + '\n')
        temporary.replace(target)

    def command(self, label, args, timeout=30, check=True, binary=False):
        self.counter += 1
        prefix = self.session / f'{self.counter:04d}-{label}'
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        # Streaming to files retains failures and sideload progress even on interruption.
        with Path(str(prefix) + '.stdout').open('wb') as out, Path(str(prefix) + '.stderr').open('wb') as err:
            try:
                result = subprocess.run(list(map(str, args)), env=self.env, stdout=out, stderr=err,
                                        timeout=timeout, **flags)
            except subprocess.TimeoutExpired:
                raise Stop('The phone did not answer in time. Leave its menu unchanged and see Help; do not repeat a flash.')
        Path(str(prefix) + '.exit').write_text(str(result.returncode))
        output = Path(str(prefix) + '.stdout').read_bytes()
        error = Path(str(prefix) + '.stderr').read_bytes()
        need(not check or result.returncode == 0,
             'A required check did not finish: ' + label + '. See the local session log and Help; no checks will be skipped.')
        if binary:
            return output
        return output.decode(errors='replace').strip()

    def adb_call(self, label, *args, **kwargs):
        need(self.serial is not None, 'No phone has been selected.')
        return self.command(label, [self.adb, '-P', '5037', '-s', self.serial, *args], **kwargs)

    def shell(self, label, *args, **kwargs):
        return self.adb_call(label, 'shell', *args, **kwargs)

    def tools(self, folder=None):
        suffix = '.exe' if os.name == 'nt' else ''
        folder = folder or self.kit / 'platform-tools'
        for name in ('adb', 'fastboot'):
            path = folder / (name + suffix)
            if not path.is_file():
                found = shutil.which(name + suffix)
                if not found:
                    folder = self.ui.file('Select the platform-tools folder (contains adb and fastboot)')
                    path = folder / (name + suffix)
                else:
                    path = Path(found)
            need(path.is_file(), 'Platform-Tools are missing. See START-HERE for the official download and extraction step.')
            setattr(self, name, path.resolve())
            self.command(name + '-version', [path, 'version' if name == 'adb' else '--version'])

    def discover(self):
        output = self.command('connected-phones', [self.adb, '-P', '5037', 'devices', '-l'])
        devices = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and re.fullmatch('[A-Za-z0-9_-]+', parts[0]):
                devices.append((parts[0], parts[1]))
        need(devices, 'No USB phone found. Unlock Android, enable USB debugging, connect USB and accept the computer prompt. Then restart the helper.')
        if len(devices) == 1:
            serial, state = devices[0]
        else:
            serial = self.ui.choice('Choose your Surface Duo 2 (disconnect other phones if unsure):',
                                    [(s, s + ' — ' + state) for s, state in devices])
            state = dict(devices)[serial]
        need(state == 'device', 'The phone is not ready in normal Android. Accept USB debugging on the phone, or return to normal Android and restart the helper. Do not choose Enable ADB in recovery.')
        need(self.serial is None or serial == self.serial, 'A different phone was selected after reconnecting. Stop and reconnect the original phone.')
        self.serial = serial
        self.save(serial=serial)
        need(self.shell('serial', 'getprop', 'ro.boot.serialno') == serial and
             self.shell('hardware', 'getprop', 'ro.hardware') == 'surfaceduo2', 'This is not the selected Surface Duo 2.')
        need(self.shell('enforcing', 'getenforce') == 'Enforcing', 'SELinux is not Enforcing. This configuration is unsupported.')
        need(self.shell('complete', 'getprop', 'sys.boot_completed') == '1', 'Wait for Android to finish starting, then restart the helper.')

    def baseline(self, mode):
        build = self.shell('source-build', 'getprop', 'ro.build.date.utc')
        device = self.shell('source-device', 'getprop', 'ro.product.device')
        if mode == 'update':
            need(build.isdigit() and int(build) <= int(self.release['build']), 'Downgrades are not supported by the update flow.')
            need(device == 'zeta' and build in self.release['sources'],
                 'This installed system is not a supported beta update source. Stop and consult the guide; the helper will not switch to an erase flow.')
            source = self.release['sources'][build]
            need(self.runtime() == source['runtime'], 'The installed system differs from the supported beta. Stop; do not wipe or bypass this check.')
            recovery = source['recovery']
        else:
            need(device == 'duo2' and self.shell('stock-version', 'getprop', 'ro.build.version.incremental') ==
                 self.release['stock_incremental'], 'First installation supports only the exact official stock version in the guide. It will not erase an unknown beta/prototype.')
            recovery = self.release['build']
        suffix = self.shell('source-slot', 'getprop', 'ro.boot.slot_suffix')
        need(suffix in ('_a', '_b'), 'The running slot could not be identified.')
        battery = self.shell('battery', 'dumpsys', 'battery')
        level = re.search(r'(?m)^\s*level:\s*(\d+)', battery)
        need(level and int(level[1]) >= 50 and 'USB powered: true' in battery,
             'Charge the phone above 50% and keep it powered by USB before continuing.')
        android_id = self.shell('userdata-id', 'settings', '--user', '0', 'get', 'secure', 'android_id')
        need(re.fullmatch('[0-9a-fA-F]{16}', android_id), 'Unlock Android and complete setup/USB authorization before continuing.')
        self.save('normal-checked', source_build=build, source_slot=suffix[-1],
                  target_slot='b' if suffix == '_a' else 'a', recovery_build=recovery,
                  battery_time=now(), battery_level=int(level[1]),
                  android_id_sha256=hashlib.sha256(android_id.encode()).hexdigest(),
                  workspace=self.shell('workspace', 'settings', 'get', 'global', 'zeta_workspace_enabled'))

    def runtime(self):
        paths = dict(RUNTIME)
        for name, package in [('systemui', 'com.android.systemui'), ('launcher', 'com.android.launcher3')]:
            value = self.shell(name + '-path', 'pm', 'path', package).removeprefix('package:')
            need(re.fullmatch(r'/[A-Za-z0-9_+=/.~\-]+', value), 'The active system app path is ambiguous.')
            paths[name] = value
        return {name: self.shell(name + '-hash', 'sha256sum', path).split()[0] for name, path in paths.items()}

    def public_key(self):
        candidates = []
        for value in self.env.get('ADB_VENDOR_KEYS', '').split(os.pathsep):
            if value:
                path = Path(value)
                candidates.append(path if path.suffix == '.pub' else Path(str(path) + '.pub'))
        home = Path(self.env.get('ANDROID_USER_HOME', str(Path.home() / '.android')))
        candidates.append(home / 'adbkey.pub')
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return self.ui.file('Select this computer\'s existing adbkey.pub (never the private adbkey)')

    def prepare(self, stock, public_key):
        self.ui.log('Checking your official recovery file and preparing the signed beta. This can take several minutes.')
        need(public_key.name.endswith('.pub') and public_key.is_file(), 'Select the public adbkey.pub file, not a private key.')
        need(stock.is_file() and sha(stock) == self.release['stock_sha256'],
             'This is not the complete supported Microsoft recovery ZIP (2023.501.541). Download the exact file in START-HERE; keep it zipped.')
        need(shutil.disk_usage(self.work).free >= 20 * 1024**3,
             'This working folder needs 20 GB free for preparation. Choose another drive or free space first.')
        if self.ota.exists():
            need(sha(self.ota) == self.release['ota_sha256'], 'An existing prepared installer is changed. Keep it for diagnosis and choose a new working folder.')
        else:
            self.command('assemble', [sys.executable, '-I', self.kit / 'assembly.py', 'assemble', '--kit', self.kit,
                                     '--stock', stock, '--output', self.ota], timeout=None)
        need(sha(stock) == self.release['stock_sha256'] and sha(self.ota) == self.release['ota_sha256'],
             'The official recovery or prepared beta does not match this release.')
        report = verify_package.verify(self.ota, self.kit / 'ota.x509.pem', self.release['certificate_sha256'])
        payload = assembly.payload(self.ota)
        expected = {p['name']: (p['size'], p['sha256']) for p in self.release['partitions']}
        need({n: (p['size'], p['sha256']) for n, p in payload['partitions'].items()} == expected,
             'The update payload does not match the audited images.')
        self.recoveries = {}
        for build, spec in self.release['recoveries'].items():
            output = self.work / ('owner-recovery-' + build + '.img')
            # Public key identity is part of a prepared recovery. Reusing a previous
            # owner's file is never allowed; build afresh into this session.
            output = self.session / output.name
            self.command('prepare-recovery-' + build, [sys.executable, '-I', self.kit / 'prepare-owner-recovery.py',
                         '--boot', safe_child(self.kit, spec['boot']), '--recipe', safe_child(self.kit, spec['recipe']),
                         '--adb-public-key', public_key, '--output', output], timeout=120)
            self.recoveries[build] = output
        self.save('files-prepared', verification=report, ota=str(self.ota), ota_sha256=sha(self.ota),
                  recoveries={k: {'path': str(v), 'sha256': sha(v)} for k, v in self.recoveries.items()})
        self.ui.log('Files verified: the beta package, its payload and metadata signatures all pass.')

    def fb(self, name):
        self.counter += 1
        label = 'bootloader-' + name.replace(':', '-')
        value = self.command(label, [self.fastboot, '-s', self.serial, 'getvar', name])
        error = (self.session / f'{self.counter:04d}-{label}.stderr').read_text(errors='replace')
        match = re.search(r'(?m)^(?:\(bootloader\)\s*)?' + re.escape(name) + r':\s*(\S+)\s*$', value + '\n' + error)
        need(match and 'FAILED' not in error, 'The bootloader did not answer a required identity check. Reconnect USB and use Help; no checks will be skipped.')
        return match[1]

    def wait(self, mode, seconds=120):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            result = self.adb_call('wait-phone', 'get-state', timeout=10, check=False)
            if result == mode:
                return
            time.sleep(2)
        raise Stop('The phone has not reconnected in the expected mode. Leave it as it is and use Help/session logs.')

    def enter_recovery(self):
        mode = self.state['mode']
        self.baseline(mode)  # Refresh battery after potentially lengthy file assembly.
        self.save('bootloader-transition-started')
        self.adb_call('to-bootloader', 'reboot', 'bootloader')
        # Wait for USB enumeration without accepting a missing identity.
        deadline = time.monotonic() + 90
        while True:
            try:
                current = self.fb('current-slot')
                break
            except Stop:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        need(current == self.state['source_slot'] and self.fb('serialno') == self.serial and
             self.fb('product') == 'surfaceduo2' and self.fb('slot-count') == '2',
             'Bootloader identity or slot changed. Stop; do not select a slot manually.')
        need(self.fb('slot-successful:' + current) == 'yes' and self.fb('slot-unbootable:' + current) == 'no',
             'The running source slot is not healthy. Stop and use Help.')
        unlocked = self.fb('unlocked')
        need(unlocked in ('yes', 'no'), 'The bootloader lock state is unknown. No unlock request will be made.')
        if unlocked == 'no':
            need(mode == 'first', 'The bootloader is locked. The update flow will not unlock or erase it.')
            self.ui.typed('Unlocking the bootloader erases this phone. Back up first. You must also confirm on the phone.', 'ERASE')
            self.save('unlock-requested', erase_consent=True)
            self.command('unlock', [self.fastboot, '-s', self.serial, 'flashing', 'unlock'], timeout=120)
            self.ui.step('On the phone, confirm bootloader unlocking. Continue only after it finishes and returns to the bootloader menu.')
            need(self.fb('unlocked') == 'yes', 'Unlocking was not confirmed. No install will be attempted.')
            self.command('return-after-unlock', [self.fastboot, '-s', self.serial, 'reboot'])
            self.ui.step('Let stock Android start. Complete its setup, enable USB debugging again and accept this computer. Then continue. This setup is temporary; first installation will format data in recovery too.')
            self.wait('device', 300)
            self.discover()
            return self.enter_recovery()
        recovery = Path(self.state['recoveries'][self.state['recovery_build']]['path'])
        need(sha(recovery) == self.state['recoveries'][self.state['recovery_build']]['sha256'], 'Prepared recovery changed.')
        self.save('matching-recovery-boot-requested')
        self.command('boot-owner-recovery', [self.fastboot, '-s', self.serial, 'boot', recovery], timeout=90)
        self.wait('recovery')
        self.state['recovery_boot_id'] = self.recovery_identity()
        self.save('recovery-connected')

    def recovery_identity(self):
        need(self.adb_call('recovery-mode', 'get-state') == 'recovery', 'Return to the recovery main menu so checks can run.')
        for prop, expected in [('ro.boot.serialno', self.serial), ('ro.product.device', 'zeta'),
                               ('ro.build.date.utc', self.state['recovery_build']),
                               ('ro.boot.slot_suffix', '_' + self.state['source_slot']), ('ro.adb.secure', '1')]:
            need(self.shell(prop, 'getprop', prop) == expected, 'The temporary recovery identity changed. Stop; do not disable ADB authentication.')
        need(self.shell('recovery-id', 'id').startswith('uid=0') and
             self.shell('recovery-enforcing', 'getenforce') == 'Enforcing' and
             self.shell('recovery-auth', 'getprop', 'ro.adb.secure.recovery') in ('', '1'), 'Recovery security checks failed.')
        raw = self.adb_call('trusted-ota-certificates', 'exec-out', 'cat', '/system/etc/security/otacerts.zip', binary=True)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = [n for n in archive.namelist() if not n.endswith('/')]
            need(len(names) == 1, 'Recovery trusts an unexpected set of OTA certificates.')
            pem = archive.read(names[0]).decode('ascii')
        body = pem.split('-----BEGIN CERTIFICATE-----')[1].split('-----END CERTIFICATE-----')[0]
        digest = hashlib.sha256(base64.b64decode(''.join(body.split()), validate=True)).hexdigest()
        need(digest == self.release['certificate_sha256'], 'Recovery does not trust the verified beta signing identity.')
        boot = self.shell('recovery-boot-id', 'cat', '/proc/sys/kernel/random/boot_id')
        need(not self.state.get('recovery_boot_id') or boot == self.state['recovery_boot_id'], 'The RAM recovery rebooted. Stop; do not continue this session.')
        return boot

    def preflight(self):
        need(not self.state.get('sender_started'), 'A sender already started. Do not repeat it; use Check last installation.')
        self.recovery_identity()
        capacity = self.shell('recovery-battery', 'if [ -r /sys/class/power_supply/battery/capacity ]; then cat /sys/class/power_supply/battery/capacity; else echo UNAVAILABLE; fi')
        if capacity == 'UNAVAILABLE':
            need(0 <= age(self.state['battery_time']) <= 900, 'The battery reading has expired. Do not install; see Help for a safe return and fresh battery check.')
        else:
            need(capacity.isdigit() and int(capacity) >= 50, 'Recovery battery is below 50%. Stop and charge safely.')
        output = self.session / ('preflight-' + str(time.time_ns()))
        self.command('slot-snapshot-check', [sys.executable, '-I', self.kit / 'preflight-owner-install.py',
                     '--adb', self.adb, '--serial', self.serial, '--expected-build', self.state['recovery_build'],
                     '--output', output], timeout=120)
        report = json.loads((output / 'preflight.json').read_text())
        need(report['state'] == 'PASS' and report['current_slot'] == self.state['source_slot'] and
             report['snapshots_none'], 'Slot/snapshot checks did not pass.')
        self.recovery_identity()
        before = self.adb_call('before-sideload-log', 'exec-out', 'cat', '/tmp/recovery.log', binary=True)
        path = self.session / 'before-sideload.log'
        path.write_bytes(before)
        self.save('preflight-passed', preflight_time=now(), before_log='before-sideload.log')

    def factory_reset(self):
        need(self.state['mode'] == 'first', 'The update flow cannot format data.')
        # Verify exact stock bytes before offering the destructive menu action.
        self.ui.log('Checking installed stock firmware before offering the data-format step…')
        actual = self.installed_stock_hashes()
        need(actual == {name: info['sha256'] for name, info in self.release['stock_partitions'].items()},
             'Installed stock firmware differs from the supported base. No erase request will be made.')
        self.save(stock_firmware_hashes=actual, stock_firmware_source_slot=self.state['source_slot'])
        self.preflight()
        self.ui.typed('FIRST INSTALLATION ERASES ALL PHONE DATA. Confirm that your backup and recovery codes are safe. The update option does not require this.', 'ERASE')
        before = self.adb_call('before-format-log', 'exec-out', 'cat', '/tmp/recovery.log', binary=True)
        self.save('owner-manual-format-requested', erase_consent=True)
        self.ui.step('On the phone select Factory reset → Format data/factory reset → Format data. When it reports completion, return to the recovery main menu. Then continue here. Do not choose System wipe.')
        self.recovery_identity()
        after = self.adb_call('after-format-log', 'exec-out', 'cat', '/tmp/recovery.log', binary=True)
        need(after.startswith(before) and b'Data wipe complete.' in after[len(before):] and
             b'Data wipe failed.' not in after[len(before):], 'A successful data format was not recorded. Stop; no OTA will be sent.')
        self.save('first-install-format-verified', format_verified=True)

    def installed_stock_hashes(self):
        # vendor/odm are logical partitions, not by-name aliases. Read their
        # checked super extents directly; never create a writable DM mapping.
        device = '/dev/block/bootdevice/by-name/super'
        total = int(self.shell('super-size', 'blockdev', '--getsize64', device))
        def read(offset, length):
            need(0 <= offset and 0 < length <= 16 * 1024 * 1024 and offset + length <= total,
                 'The stock read is outside the physical super partition.')
            sector, padding = divmod(offset, 512)
            count = (padding + length + 511) // 512
            raw = self.adb_call('read-stock-super', 'exec-out',
                               f'dd if={device} bs=512 skip={sector} count={count} 2>/dev/null',
                               binary=True, timeout=120)
            need(len(raw) == count * 512, 'The phone returned an incomplete stock read.')
            return raw[padding:padding + length]
        slot = self.state['source_slot']
        mappings = stock_layout.inspect(read, total, slot)
        result = {name: stock_layout.prefix_hash(read, mappings[name + '_' + slot],
                                                self.release['stock_partitions'][name]['size'])
                  for name in ('vendor', 'odm')}
        for name in ('vendor_boot', 'dtbo'):
            count = self.release['stock_partitions'][name]['size']
            path = '/dev/block/bootdevice/by-name/' + name + '_' + slot
            result[name] = self.shell('stock-' + name, f'head -c {count} {path} | sha256sum', timeout=120).split()[0]
        return result

    def send(self):
        self.preflight()
        self.ui.step('On the phone choose Apply update → Apply from ADB. Leave the cable connected. Once the phone says it is waiting for a package, continue here. Never choose Enable ADB.')
        need(not self.state.get('sender_started') and sha(self.ota) == self.release['ota_sha256'],
             'A sender already exists or the prepared update changed. No second sender will start.')
        need(self.adb_call('manual-sideload-mode', 'get-state') == 'sideload', 'The phone is not in Apply from ADB. No package was sent.')
        # Hashing a multi-gigabyte file takes time. Check freshness AFTER the
        # last slow check, immediately before writing the one-shot sender ledger.
        need(0 <= age(self.state['preflight_time']) <= 120 and
             0 <= age(self.state['battery_time']) <= 900,
             'The checks expired while waiting. Cancel sideload on the phone, return to the main menu and use Help. No package was sent.')
        self.save('sending', sender_started=True, sender_time=now())
        self.ui.log('Installing. Keep USB connected. A host progress reading near 47% can be normal. If asked about additional apps, choose No, then leave the recovery menu open.')
        self.adb_call('actual-sideload', 'sideload', self.ota, timeout=None)
        self.save('sender-finished', sender_exit=0)
        self.ui.step('Wait for recovery to finish. If asked to install additional apps, choose No. Leave the recovery main menu open and continue here. Do not reboot yet.')
        self.verify_install()

    def verify_install(self):
        self.recovery_identity()
        after = self.adb_call('postinstall-log', 'exec-out', 'cat', '/tmp/recovery.log', binary=True)
        need(self.state['before_log'] == 'before-sideload.log', 'This session has an unexpected recovery-log reference. Stop and use Help.')
        before = (self.session / 'before-sideload.log').read_bytes()
        need(after.startswith(before), 'Recovery log changed; this session cannot prove the installation.')
        text = after[len(before):].decode(errors='replace')
        statuses = re.findall(r'(?:Install from ADB complete \(status: (\d+)\)|Install completed with status (\d+)\.)', text)
        need(statuses and next(v for v in statuses[-1] if v) == '0' and
             'PostinstallRunnerAction with code ErrorCode::kSuccess' in text and
             'Update successfully applied, waiting to reboot.' in text,
             'Recovery did not record a successful installation. Do not reboot, wipe, or switch slots; use Help.')
        need('whole-file signature verified against RSA key 0' in text and
             re.search(r'Update package verification took [\d.]+ s \(result 0\)', text) and
             re.findall(r'target_build:\s*(\d+)', text)[-1:] == [self.release['build']],
             'Recovery signature verification or target build differs. Stop; never bypass the warning.')
        actual = dict((n, h.lower()) for n, h in re.findall(r'Hash of ([a-z_]+): ([A-Fa-f0-9]{64})', text))
        expected = {p['name']: p['sha256'] for p in self.release['partitions']}
        need(len(actual) == 10 and actual == expected, 'Installed partition verification failed. Leave recovery open and use Help.')
        slots = json.loads(self.shell('postinstall-slots', 'timeout', '20s', '/system/bin/zeta-slot-status'))
        source, target = (0 if self.state[n] == 'a' else 1 for n in ('source_slot', 'target_slot'))
        ufs = int(self.shell('postinstall-ufs', 'cat', UFS), 0)
        need(slots['slots'] == 2 and slots['current'] == source and slots['active'] == target and
             slots['merge_status'] in (0, 2) and ufs == target + 1 and
             slots['slot_state'][target]['bootable'] and not slots['slot_state'][target]['successful'],
             'The boot controller does not match the completed update. Do not select a slot yourself.')
        digest = self.shell('direct-target-boot', 'sha256sum', '/dev/block/bootdevice/by-name/boot_' + self.state['target_slot'], timeout=120).split()[0]
        need(digest == expected['boot'], 'The installed boot image does not match.')
        self.save('installation-verified', recovery_signature_result=0, actual_install_status=0,
                  all_ten_installed_hashes_match=True, direct_target_boot_sha256=digest,
                  postinstall_slots=slots, postinstall_ufs=ufs)

    def finish(self):
        need(self.state['phase'] == 'installation-verified', 'Unverified installations will not be rebooted automatically.')
        self.verify_install()
        need(not self.state.get('normal_reboot_requested'), 'A normal reboot has already been requested.')
        self.save('normal-reboot-requested', normal_reboot_requested=True)
        self.start_boot_capture(self.state['recovery_boot_id'])
        self.adb_call('normal-reboot', 'reboot')
        self.ui.step('Let Android start. For an update, unlock with your existing PIN. For a first install, complete setup, enable USB debugging and accept this computer again. Keep USB connected, then continue here.')
        self.wait('device', 300)
        self.validate_normal()
        self.first_install_preferences()
        self.finished_message()

    def validate_normal(self):
        boot = self.normal_identity()
        checkpoint = self.shell('early-boot-checkpoint', 'logcat', '-b', 'all', '-d', '-s', 'vold:V', 'Checkpoint:V', 'bootctrl:V', 'zeta.bootctrl:V')
        self.ui.log('The new beta is running. Checking that Android stays stable for two minutes…')
        attempt = self.session / ('validation-' + str(time.time_ns()))
        attempt.mkdir(mode=0o700)
        self.save(validation_attempt=str(attempt))
        samples = []
        started = time.monotonic()
        for index in range(5):
            if index:
                time.sleep(30)
            need(self.normal_identity() == boot, 'Android restarted during validation. Keep the local logs and use Help.')
            row = {'elapsed': time.monotonic() - started, 'boot_id': boot}
            for name, process in [('system_server', 'system_server'), ('systemui', 'com.android.systemui'), ('launcher', 'com.android.launcher3')]:
                row[name] = self.shell(name + '-' + str(index), 'pidof', process)
                need(row[name].isdigit(), 'A core Android process is not ready. Use Help; do not reinstall automatically.')
            need(not samples or all(row[n] == samples[0][n] for n in ('system_server', 'systemui', 'launcher')),
                 'A core Android process restarted. Validation stopped; keep the logs.')
            samples.append(row)
            (attempt / 'stability.json').write_text(json.dumps(samples, indent=2))
        need(samples[-1]['elapsed'] >= 120, 'Stability observation was too short.')
        checkpoint += '\n' + self.shell('final-boot-checkpoint', 'logcat', '-b', 'all', '-d', '-s', 'vold:V', 'Checkpoint:V', 'bootctrl:V', 'zeta.bootctrl:V')
        crash = self.shell('crash-buffer', 'logcat', '-b', 'crash', '-d')
        self.close_capture()
        checkpoint += '\n' + self.captured_boot_text(boot)
        evidence = boot_evidence(checkpoint, self.prior_committed_validation_context())
        (attempt / 'boot-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        need(not re.search(r'FATAL EXCEPTION|Fatal signal|Abort message', crash), 'Android recorded a fatal crash. Keep the logs and report it.')
        self.save('complete', error=False, boot_id=boot, stability_seconds=samples[-1]['elapsed'], boot_success=True,
                  checkpoint_committed=evidence['checkpoint_committed_this_boot'],
                  checkpoint_status=evidence['checkpoint_status'], no_fatal_crash=True)

    def check_session(self, state_path, tools=None):
        """Never starts another sender for a session whose sender already began."""
        need(state_path.is_file() and state_path.name == 'state.json' and
             state_path.resolve().is_relative_to(self.work), 'Choose state.json inside this working folder.')
        with contextlib.ExitStack() as locks:
            locks.enter_context(PhoneLock(self.work))
            locks.enter_context(PhoneLock(phone_lock_root()))
            self.session = state_path.parent
            self.state = json.loads(state_path.read_text())
            self.counter = max([int(p.name.split('-', 1)[0]) for p in self.session.glob('*.stdout')
                                if p.name.split('-', 1)[0].isdigit()] or [0]) + 1000
            need(self.state['target_build'] == self.release['build'] and
                 re.fullmatch('[A-Za-z0-9_-]+', self.state.get('serial', '')),
                 'This session is not for this release or has no selected phone.')
            need(self.state['mode'] in ('first', 'update') and
                 self.state.get('source_slot') in ('a', 'b') and
                 self.state.get('target_slot') in ('a', 'b') and
                 self.state['source_slot'] != self.state['target_slot'] and
                 self.state.get('recovery_build') in self.release['recoveries'],
                 'The saved operation identity is invalid. No phone command will be sent.')
            if self.state['mode'] == 'update':
                profile = self.release['sources'].get(self.state.get('source_build'))
                need(profile and profile['recovery'] == self.state['recovery_build'],
                     'The saved update source is unsupported. No phone command will be sent.')
            self.serial = self.state['serial']
            need(self.ota.is_file() and sha(self.ota) == self.release['ota_sha256'], 'The prepared package is missing or changed.')
            verify_package.verify(self.ota, self.kit / 'ota.x509.pem', self.release['certificate_sha256'])
            self.tools(tools)
            mode = self.adb_call('check-current-mode', 'get-state')
            if mode == 'device':
                need(self.state.get('all_ten_installed_hashes_match') and
                     self.state.get('actual_install_status') == 0,
                     'Android is connected, but this session has no verified recovery result. Keep the logs and ask for help; do not reinstall or switch slots.')
                if self.state['phase'] == 'complete':
                    self.normal_identity()
                    self.ui.log('The current beta matches this completed installation. No phone changes were made.')
                else:
                    choice = self.ui.choice('Finish this installed beta. No option sends another package or erases data.',
                         [('current', 'Check the current boot (no reboot)'),
                          ('reboot', 'Reboot once to capture and verify startup'),
                          ('workspace', 'Enable independent left/right workspace and reboot once')])
                    if choice in ('reboot', 'workspace'):
                        self.validation_reboot(enable_workspace=choice == 'workspace')
                    else:
                        need(choice == 'current', 'Cancelled.')
                        self.ui.step('Unlock Android with your PIN privately, then continue to finish checks. No transfer or reboot will start.')
                        self.validate_normal()
                    self.first_install_preferences()
                    self.finished_message()
            elif mode == 'recovery':
                self.recovery_identity()
                if self.state.get('sender_started'):
                    self.verify_install()
                    need(not self.state.get('normal_reboot_requested'),
                         'A reboot was already requested but recovery is still connected. Do not repeat it automatically; keep the logs and use Help.')
                    self.ui.confirm('Recovery proves the update succeeded. Continue with one normal reboot and validation?')
                    self.finish()
                else:
                    need(self.state['mode'] == 'update' or self.state.get('format_verified'),
                         'This first-install session has no verified data-format stage. Use Help before proceeding; no erase or transfer was repeated.')
                    self.ui.confirm('This prepared session has not sent a package. Continue with fresh checks and the manual recovery-menu step?')
                    self.send()
                    self.finish()
            else:
                raise Stop('The phone is still in sideload or another mode. Let installation finish, choose No for additional apps, and return to recovery main menu. No second sender was started.')

    def normal_identity(self):
        for prop, expected in [('ro.boot.serialno', self.serial), ('ro.product.device', 'zeta'),
                               ('ro.build.date.utc', self.release['build']),
                               ('ro.boot.slot_suffix', '_' + self.state['target_slot']), ('sys.boot_completed', '1')]:
            need(self.shell('new-' + prop, 'getprop', prop) == expected, 'The expected new Android system is not ready or differs from this release.')
        need(self.shell('new-enforcing', 'getenforce') == 'Enforcing' and self.runtime() == self.release['runtime'],
             'The running Android code/security state differs from the verified beta.')
        self.verify_default_workspace()
        if self.state['mode'] == 'update':
            android_id = self.shell('retained-userdata', 'settings', '--user', '0', 'get', 'secure', 'android_id')
            need(hashlib.sha256(android_id.encode()).hexdigest() == self.state['android_id_sha256'] and
                 self.shell('retained-workspace', 'settings', 'get', 'global', 'zeta_workspace_enabled') == self.state.get('validation_workspace', self.state['workspace']),
                 'The retained data/workspace identity differs. Stop and keep your logs.')
        need(self.shell('setup-done', 'settings', '--user', '0', 'get', 'secure', 'user_setup_complete') == '1' and
             self.shell('provisioned', 'settings', 'get', 'global', 'device_provisioned') == '1',
             'Complete Android setup and unlock, then use Check last installation.')
        boot = self.shell('new-boot-id', 'cat', '/proc/sys/kernel/random/boot_id')
        need(boot != self.state['recovery_boot_id'], 'The phone is still in the temporary boot.')
        if self.state.get('validation_reboot_requested'):
            need(boot != self.state['validation_previous_boot_id'], 'The requested normal reboot has not happened. Do not repeat it automatically.')
            android_id = self.shell('validation-retained-userdata', 'settings', '--user', '0', 'get', 'secure', 'android_id')
            need(hashlib.sha256(android_id.encode()).hexdigest() == self.state['validation_android_id_sha256'] and
                 self.shell('validation-retained-workspace', 'settings', 'get', 'global', 'zeta_workspace_enabled') == self.state['validation_workspace'],
                 'Data or the selected layout changed during validation reboot.')
        return boot

    def run(self, mode, stock, public_key=None, tools=None):
        need(mode in ('prepare', 'first', 'update'), 'Unsupported mode; no phone operation will start.')
        with contextlib.ExitStack() as locks:
            locks.enter_context(PhoneLock(self.work))
            if mode != 'prepare':
                locks.enter_context(PhoneLock(phone_lock_root()))
            self.begin(mode)
            if mode == 'prepare':
                need(public_key is not None, 'Preparation needs an existing adbkey.pub.')
                self.prepare(stock, public_key)
                self.save('preparation-complete-no-device-commands')
                self.ui.log('Preparation complete. No phone was queried or changed.')
                return
            self.tools(tools)
            self.discover()
            self.baseline(mode)
            self.ui.confirm('Ready to ' + ('update your compatible beta without a planned wipe' if mode == 'update' else
                            'prepare a FIRST installation; unlocking and formatting erase the phone') +
                            '. Make a current backup first. Phone: ' + self.serial + '. Continue only for your Surface Duo 2.')
            self.prepare(stock, public_key or self.public_key())
            self.enter_recovery()
            if mode == 'first':
                self.factory_reset()
            self.send()
            self.finish()


def default_work():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Duo2Beta'
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'duo2-beta'


def phone_lock_root():
    # Independent of the chosen kit/working folder. Two copies cannot race a
    # device operation simply by choosing different output locations.
    root = default_work()
    return root.with_name(root.name + '-locks')


def workflow(ui, args):
    kit = Path(__file__).resolve().parent
    ui.log('Checking the installer kit…')
    release = load_release(kit)
    load_dependencies(kit, release)
    ui.log('Surface Duo 2 beta — ' + release['label'] + '. See validation notes in the guide.')
    mode = 'prepare' if args.prepare_only else ui.choice('What would you like to do?',
           [('update', 'Update an existing compatible beta (keep apps/data)'),
            ('first', 'First installation from supported stock Android (ERASES DATA)'),
            ('prepare', 'Prepare files only (no phone changes)'),
            ('check', 'Check an unfinished or completed installation (never resends a started update)')])
    work = args.work or ui.file('Choose a working folder with at least 20 GB free', str(default_work()))
    installer = Installer(kit, work, ui, release)
    if mode == 'check':
        state = ui.file('Select the session state.json from your working folder')
        try:
            installer.check_session(state, args.tools)
            installer.close_capture()
        except BaseException:
            record_failure(installer, ui)
            raise
        return
    stock = args.stock or ui.file('Select the official Microsoft recovery ZIP listed in START-HERE')
    public_key = args.public_key
    if mode == 'prepare' and public_key is None:
        public_key = ui.file('Select your existing adbkey.pub (public key only)')
    try:
        installer.run(mode, stock, public_key, args.tools)
        installer.close_capture()
    except BaseException:
        record_failure(installer, ui)
        raise


def record_failure(installer, ui):
    installer.close_capture()
    if installer.session:
        failure = installer.session / ('failure-' + str(time.time_ns()) + '.txt')
        failure.write_text(traceback.format_exc())
        installer.save(error=True, latest_failure=str(failure))
        ui.log('Local session logs: ' + str(installer.session))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--console', action='store_true')
    parser.add_argument('--prepare-only', action='store_true', help='No device commands')
    parser.add_argument('--stock', type=Path)
    parser.add_argument('--public-key', type=Path)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--tools', type=Path)
    args = parser.parse_args()
    need(sys.version_info >= (3, 11), 'Python 3.11 or newer is required. See START-HERE.')
    require_normal_user()
    root = Path(__file__).resolve().parent
    release = load_release(root)
    load_dependencies(root, release)
    # The GUI's need/Stop imports must resolve to this already-verified engine.
    sys.modules['installer'] = sys.modules[__name__]
    if not args.console and not args.prepare_only:
        try:
            installer_ui = verified_module(root, release, 'installer_ui', 'installer_ui.py')
        except ImportError:
            print('Window support is unavailable; using the same guided steps in this terminal.')
        else:
            try:
                installer_ui.run(lambda ui: workflow(ui, args))
                return
            except installer_ui.UIUnavailable:
                print('A window could not be opened; using the same guided steps in this terminal.')
    try:
        workflow(Console(), args)
    except (Exception, KeyboardInterrupt) as error:
        print('\nStopped safely: ' + str(error), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
