// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacepermissiontests;

import android.app.Instrumentation;
import android.app.UiAutomation;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.MotionEvent;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import static org.junit.Assert.*;
import static org.junit.Assume.assumeTrue;

/** Emulator-only coherent swipe-and-hold; no app permission or persistent grant. */
public class GestureInjectionTest {
    @Test public void swipeAndHoldForOverview() throws Exception {
        Bundle args = InstrumentationRegistry.getArguments();
        assumeTrue("overview".equals(args.getString("zeta_gesture")));
        assertEquals("lineage_zeta_workspace_emu", android.os.SystemProperties.get("ro.product.name"));
        assertTrue("1".equals(android.os.SystemProperties.get("ro.boot.qemu"))
                || "1".equals(android.os.SystemProperties.get("ro.kernel.qemu")));
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        UiAutomation automation = instrumentation.getUiAutomation();
        int panel = Integer.parseInt(args.getString("zeta_panel", "1"));
        assertTrue(panel == 0 || panel == 1);
        float x = panel == 0 ? 672 : 2082;
        long down = SystemClock.uptimeMillis();
        inject(automation, down, MotionEvent.ACTION_DOWN, x, 1886);
        for (int i = 1; i <= 20; i++) {
            SystemClock.sleep(16);
            inject(automation, down, MotionEvent.ACTION_MOVE, x, 1886 - 836 * i / 20f);
        }
        Bundle status = new Bundle(); status.putString("stream", "ZETA_GESTURE_HOLD\n");
        instrumentation.sendStatus(1, status);
        try { SystemClock.sleep(1500); }
        finally { inject(automation, down, MotionEvent.ACTION_UP, x, 1050); }
    }
    @Test public void tossExistingTask() throws Exception {
        Bundle args=InstrumentationRegistry.getArguments();
        assumeTrue("toss".equals(args.getString("zeta_gesture")));
        assertEquals("lineage_zeta_workspace_emu",android.os.SystemProperties.get("ro.product.name"));
        assertTrue(android.os.SystemProperties.getBoolean("ro.boot.qemu",false)
                || android.os.SystemProperties.getBoolean("ro.kernel.qemu",false));
        UiAutomation automation=InstrumentationRegistry.getInstrumentation().getUiAutomation();
        automation.adoptShellPermissionIdentity(android.Manifest.permission.MANAGE_ACTIVITY_TASKS);
        try {
            int panel=Integer.parseInt(args.getString("zeta_panel","0"));
            assertTrue(panel==0 || panel==1);
            Bundle state=android.view.WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
            assertTrue(state.getBoolean("enabled"));assertFalse(state.getBoolean("locked"));
            assertEquals(2,state.getInt("composition"));
            android.graphics.Rect from=state.getParcelable("bounds_"+panel,android.graphics.Rect.class);
            android.graphics.Rect to=state.getParcelable("bounds_"+(1-panel),android.graphics.Rect.class);
            float x=from.centerX(),y=from.bottom-6;
            long down=SystemClock.uptimeMillis();inject(automation,down,MotionEvent.ACTION_DOWN,x,y);
            for(int i=1;i<=8;i++){SystemClock.sleep(12);injectAsync(automation,down,MotionEvent.ACTION_MOVE,x,y-200*i/8f);}
            y-=200;
            float dx=to.centerX()-from.centerX(),dy=to.centerY()-from.centerY();
            if(dy<0 && Math.abs(dy)>Math.abs(dx)) {
                for(int i=1;i<=4;i++){SystemClock.sleep(12);injectAsync(automation,down,MotionEvent.ACTION_MOVE,x+140*i/4f,y);}
                x+=140;
            }
            float length=(float)Math.hypot(dx,dy);dx=dx/length*450;dy=dy/length*450;
            for(int i=1;i<=5;i++){SystemClock.sleep(12);injectAsync(automation,down,MotionEvent.ACTION_MOVE,x+dx*i/5f,y+dy*i/5f);}
            inject(automation,down,MotionEvent.ACTION_UP,x+dx,y+dy);
        }finally{automation.dropShellPermissionIdentity();}
    }

    @Test public void doubleTapScreenSelection() throws Exception {
        Bundle args=InstrumentationRegistry.getArguments();
        assumeTrue("selection".equals(args.getString("zeta_gesture")));
        assertEquals("lineage_zeta_workspace_emu",android.os.SystemProperties.get("ro.product.name"));
        assertTrue(android.os.SystemProperties.getBoolean("ro.boot.qemu",false)
                || android.os.SystemProperties.getBoolean("ro.kernel.qemu",false));
        UiAutomation automation=InstrumentationRegistry.getInstrumentation().getUiAutomation();
        automation.adoptShellPermissionIdentity(android.Manifest.permission.MANAGE_ACTIVITY_TASKS);
        try {
            int panel=Integer.parseInt(args.getString("zeta_panel","0"));assertTrue(panel==0 || panel==1);
            Bundle state=android.view.WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
            assertTrue(state.getBoolean("switching"));
            android.graphics.Rect bounds=state.getParcelable("bounds_"+panel,android.graphics.Rect.class);
            for(int tap=0;tap<2;tap++) {
                long down=SystemClock.uptimeMillis();
                injectAsync(automation,down,MotionEvent.ACTION_DOWN,bounds.centerX(),bounds.centerY());
                SystemClock.sleep(45);
                injectAsync(automation,down,MotionEvent.ACTION_UP,bounds.centerX(),bounds.centerY());
                SystemClock.sleep(100);
            }
            SystemClock.sleep(200);
        }finally{automation.dropShellPermissionIdentity();}
    }

    private static void injectAsync(UiAutomation automation,long down,int action,float x,float y) {
        MotionEvent event=MotionEvent.obtain(down,SystemClock.uptimeMillis(),action,x,y,0);
        event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
        try {assertTrue(automation.injectInputEvent(event,false,false));}finally{event.recycle();}
    }
    private static void inject(UiAutomation automation, long down, int action, float x, float y) {
        MotionEvent event = MotionEvent.obtain(down, SystemClock.uptimeMillis(), action, x, y, 0);
        event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
        try { assertTrue(automation.injectInputEvent(event, true)); }
        finally { event.recycle(); }
    }
}
