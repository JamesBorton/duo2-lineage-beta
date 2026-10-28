// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacepermissiontests;

import static org.junit.Assert.assertEquals;
import android.app.ActivityManager;
import android.content.Intent;
import android.os.Parcel;
import com.android.systemui.shared.recents.model.Task;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public final class WorkspaceTaskParcelTest {
    @Test public void recentTaskInfoRetainsPhysicalOwnerAndUnrelatedFields() {
        ActivityManager.RecentTaskInfo info = new ActivityManager.RecentTaskInfo();
        info.token = new android.window.WindowContainerToken(new android.window.IWindowContainerToken.Stub() { });
        info.taskId = 501;
        info.displayId = 0;
        info.userId = 10;
        info.baseIntent = new Intent(Intent.ACTION_VIEW);
        info.zetaWorkspacePanel = 1;
        Parcel parcel = Parcel.obtain();
        try {
            info.writeToParcel(parcel, 0);
            parcel.setDataPosition(0);
            ActivityManager.RecentTaskInfo copy = ActivityManager.RecentTaskInfo.CREATOR.createFromParcel(parcel);
            assertEquals(1, copy.zetaWorkspacePanel);
            assertEquals(info.token.asBinder(), copy.token.asBinder());
            assertEquals(501, copy.taskId);
            assertEquals(10, copy.userId);
            assertEquals(Intent.ACTION_VIEW, copy.baseIntent.getAction());
        } finally { parcel.recycle(); }
    }
    @Test public void quickstepTaskKeyRetainsPhysicalOwnerAcrossPrivateParcel() {
        ActivityManager.RecentTaskInfo info = new ActivityManager.RecentTaskInfo();
        info.token = new android.window.WindowContainerToken(new android.window.IWindowContainerToken.Stub() { });
        info.taskId = 502;
        info.baseIntent = new Intent(Intent.ACTION_MAIN);
        info.zetaWorkspacePanel = 0;
        Task.TaskKey key = new Task.TaskKey(info);
        Parcel parcel = Parcel.obtain();
        try {
            key.writeToParcel(parcel, 0);
            parcel.setDataPosition(0);
            Task.TaskKey copy = Task.TaskKey.CREATOR.createFromParcel(parcel);
            assertEquals(0, copy.zetaWorkspacePanel);
            assertEquals(502, copy.id);
            assertEquals(Intent.ACTION_MAIN, copy.baseIntent.getAction());
        } finally { parcel.recycle(); }
    }
}
