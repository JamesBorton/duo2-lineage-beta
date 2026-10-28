#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise slot/UFS/snapshot guard decisions without invoking ADB."""
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('preflight',Path(__file__).with_name('preflight-owner-install.py'))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class SlotGuards(unittest.TestCase):
    def state(self,current=0):return {'slots':2,'current':current,'active':current,'merge_status':0,
        'slot_state':[{'bootable':True,'successful':True},{'bootable':True,'successful':True}]}
    def test_healthy_a(self):self.assertEqual(mod.assess_slots(self.state(),'_a',1),0)
    def test_healthy_b(self):self.assertEqual(mod.assess_slots(self.state(1),'_b',2),1)
    def test_active_disagrees(self):
        value=self.state();value['active']=1
        with self.assertRaises(ValueError):mod.assess_slots(value,'_a',1)
    def test_unsuccessful_source(self):
        value=self.state();value['slot_state'][0]['successful']=False
        with self.assertRaises(ValueError):mod.assess_slots(value,'_a',1)
    def test_pending_merge(self):
        value=self.state();value['merge_status']=2
        with self.assertRaises(ValueError):mod.assess_slots(value,'_a',1)
    def test_wrong_ufs(self):
        with self.assertRaises(ValueError):mod.assess_slots(self.state(),'_a',2)
    def test_wrong_kernel_suffix(self):
        with self.assertRaises(ValueError):mod.assess_slots(self.state(),'_b',1)

if __name__=='__main__':unittest.main()
