#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only recovery slot/snapshot preflight. Never wipes, flashes or selects slots.

Run only in the matching owner-authorized temporary recovery. The sole mount is
metadata with ro,noload, followed by unmount. Stop on any failed check; a PASS is
not authorization to install and must be refreshed immediately before sideload.
Keep output private: it identifies your phone.
"""
import argparse,datetime,json,re,subprocess
from pathlib import Path

UFS='/sys/bus/platform/devices/1d84000.ufshc/attributes/boot_lun_enabled'


def require(value,message):
    if not value:raise ValueError(message)


def assess_slots(value,suffix,ufs):
    require(value['slots']==2,'Expected two slots')
    current=value['current'];require(current in (0,1),'Invalid slot')
    require(value['active']==current,'Active and running slots differ; inspect before installing')
    require(value['merge_status']==0,'Snapshot merge status is not NONE')
    health=value['slot_state'][current]
    require(health['bootable'] and health['successful'],'Current slot is not healthy/successful')
    require(suffix==('_a' if current==0 else '_b'),'Kernel slot property disagrees with QTI controller')
    require(ufs==current+1,'UFS boot LUN disagrees with current slot')
    return current


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adb',type=Path,required=True)
    ap.add_argument('--serial',required=True,help='Explicit USB serial from your platform-tools; never auto-select')
    ap.add_argument('--expected-build',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    require(re.fullmatch('[A-Za-z0-9_-]+',a.serial),'Expected a USB serial')
    require(a.expected_build.isdigit(),'Expected numeric release build identity')
    require(not a.output.exists(),'Output already exists')
    a.output.mkdir(parents=True)
    flags={'creationflags':subprocess.CREATE_NO_WINDOW} if hasattr(subprocess,'CREATE_NO_WINDOW') else {}
    def adb(label,*args):
        p=subprocess.run([str(a.adb),'-s',a.serial,*args],capture_output=True,timeout=30,**flags)
        (a.output/(label+'.stdout')).write_bytes(p.stdout);(a.output/(label+'.stderr')).write_bytes(p.stderr)
        require(p.returncode==0,'ADB command failed: '+label)
        return p.stdout.decode(errors='replace').strip()
    def sh(label,*args):return adb(label,'shell',*args)
    require(adb('state','get-state')=='recovery','Expected recovery with enabled authorized ADB')
    require(sh('serial','getprop','ro.boot.serialno')==a.serial,'Device serial mismatch')
    require(sh('device','getprop','ro.product.device')=='zeta','Expected zeta recovery')
    require(sh('build','getprop','ro.build.date.utc')==a.expected_build,'Wrong recovery build')
    require(sh('selinux','getenforce')=='Enforcing','SELinux must remain Enforcing')
    require(sh('secure-adb','getprop','ro.adb.secure')=='1','ADB authentication must remain enabled')
    require(sh('secure-recovery-adb','getprop','ro.adb.secure.recovery') in ('','1'),'Recovery ADB authentication was disabled; reboot matching owner recovery')
    require('uid=0' in sh('id','id'),'Recovery root is required for read-only checks')
    suffix=sh('slot-property','getprop','ro.boot.slot_suffix')
    value=json.loads(sh('slots','timeout','20s','/system/bin/zeta-slot-status'))
    ufs=int(sh('ufs','cat',UFS),0);current=assess_slots(value,suffix,ufs)
    def metadata_rows(text):return [line.split() for line in text.splitlines() if len(line.split())>3 and line.split()[1]=='/metadata']
    require(not metadata_rows(sh('mounts-before','cat','/proc/mounts')),'Metadata already mounted; stop and inspect')
    mounted=False
    try:
        sh('mount-metadata-readonly','mount','-t','ext4','-o','ro,noload','/dev/block/bootdevice/by-name/metadata','/metadata');mounted=True
        entries=metadata_rows(sh('mounts-readonly','cat','/proc/mounts'))
        require(len(entries)==1 and entries[0][2]=='ext4','Unexpected metadata mount')
        options=set(entries[0][3].split(','))
        require('ro' in options and bool({'noload','norecovery'}&options),'Metadata is not mounted ro,noload')
        state_size=sh('snapshot-state-size','if [ -e /metadata/ota/state ]; then stat -c %s /metadata/ota/state; else echo ABSENT; fi')
        # A fresh formatted metadata filesystem has no state file. AOSP
        # SnapshotManager treats ENOENT as NONE; still require no records and
        # QTI merge_status==0, and keep the mount strictly ro,noload.
        require(state_size in ('0','ABSENT'),'Snapshot state is nonempty')
        require(not sh('snapshot-records','if [ -d /metadata/ota/snapshots ]; then find /metadata/ota/snapshots -mindepth 1 -print; fi'),'Snapshot records exist')
    finally:
        if mounted:sh('unmount-metadata','umount','/metadata')
    require(not metadata_rows(sh('mounts-after','cat','/proc/mounts')),'Metadata remained mounted')
    final=json.loads(sh('final-slots','timeout','20s','/system/bin/zeta-slot-status'))
    require(assess_slots(final,sh('final-slot-property','getprop','ro.boot.slot_suffix'),int(sh('final-ufs','cat',UFS),0))==current,'Slot state changed')
    require(sh('final-selinux','getenforce')=='Enforcing','SELinux changed')
    report={'state':'PASS','time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_build':a.expected_build,
        'current_slot':'a' if current==0 else 'b','ufs_boot_lun':ufs,'slot_status':final,
        'snapshots_none':True,'metadata_mounted_readonly_and_unmounted':True,'wipe_or_flash_or_slot_mutation_performed':False,
        'install_authorized':False,'fresh_check_required_immediately_before_sideload':True}
    (a.output/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
