// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacepermissiontests;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.content.pm.PackageManager;
import android.os.Process;
import android.view.WindowManagerGlobal;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public final class WorkspacePermissionTest {
    private void verifyUnprivilegedCaller() {
        assertTrue(Process.myUid() >= 10000);
        assertEquals(PackageManager.PERMISSION_DENIED,
                InstrumentationRegistry.getInstrumentation().getTargetContext()
                        .checkSelfPermission(android.Manifest.permission.MANAGE_ACTIVITY_TASKS));
    }
    @Test public void stateReadRequiresTaskManagementPermission() throws Exception {
        verifyUnprivilegedCaller();
        try {
            WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
            fail("Unprivileged app could read workspace controller state");
        } catch (SecurityException expected) { }
    }
    @Test public void actionsAreRejectedBeforeTaskValidationOrMutation() throws Exception {
        verifyUnprivilegedCaller();
        for (int action : new int[] {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}) {
            try {
                WindowManagerGlobal.getWindowManagerService().zetaWorkspaceAction(action, 0, -1);
                fail("Unprivileged app could drive workspace action " + action);
            } catch (SecurityException expected) { }
        }
    }
}
