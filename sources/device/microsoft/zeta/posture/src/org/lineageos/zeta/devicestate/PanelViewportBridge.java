// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;

import android.content.ComponentName;
import android.content.Context;
import android.content.BroadcastReceiver;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Point;
import android.hardware.display.DisplayManagerInternal;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.ResultReceiver;
import android.provider.Settings;
import android.util.Slog;
import android.view.IWindowManager;
import android.view.WindowManagerGlobal;
import com.android.server.LocalServices;
import com.android.server.wm.WindowManagerInternal;
import java.util.function.IntSupplier;
import org.lineageos.zeta.posture.PostureContract;

/** Signature-guarded viewport operations. Surface HALs remain in platform_app. */
final class PanelViewportBridge {
    static final String ACTION = PostureContract.VIEWPORT;
    static final String PERMISSION = PostureContract.PERMISSION;
    static final String SAFE = PostureContract.SAFE;
    private static final String BASELINE = "zeta_panel_viewport_baseline";
    private final Context context;
    private final IntSupplier state;
    private final java.util.function.IntPredicate select;
    private final Handler worker;
    private int applied = -1;
    private final Runnable expired;
    private void expireLease() {
        Slog.e("ZetaViewport", "Controller lease expired; restoring and pausing");
        Settings.Global.putInt(context.getContentResolver(), SAFE, 1);
        try { apply(2); } catch (Exception error) { Slog.e("ZetaViewport", "Lease restore", error); }
        Intent restore = new Intent("org.lineageos.zeta.action.SAFE_RESTORE");
        restore.setComponent(new ComponentName("org.lineageos.zeta.posturecontroller",
                "org.lineageos.zeta.posturecontroller.SafeRestoreReceiver"));
        context.sendBroadcast(restore);
    }
    PanelViewportBridge(Context context, IntSupplier state, java.util.function.IntPredicate select) {
        this.context = context;this.state = state;this.select = select;
        expired = this::expireLease;
        HandlerThread thread = new HandlerThread("ZetaViewport");thread.start();
        worker = new Handler(thread.getLooper());
    }
    void start() {
        context.registerReceiver(new BroadcastReceiver() {
            @Override public void onReceive(Context ignored, Intent intent) {
                ResultReceiver reply = null;
                int mode = -1;
                int pause = -1;
                Bundle result = new Bundle();
                try {
                    reply = intent.getParcelableExtra("reply", ResultReceiver.class);
                    mode=intent.getIntExtra("mode",-1);pause=intent.getIntExtra("pause",-1);
                    if (mode < 0 || mode > 2 || pause < -1 || pause > 1 || (pause >= 0 && mode != 2)) {
                        throw new IllegalArgumentException("Invalid viewport request");
                    }
                    int capture = intent.getIntExtra("capture", -1);
                    int choice = intent.getIntExtra("select", -1);
                    WindowManagerInternal windows = LocalServices.getService(WindowManagerInternal.class);
                    if (choice >= 0) {
                        if (mode != 2 || pause != -1 || !select.test(choice)) throw new IllegalStateException("Selection unavailable");
                        if (reply != null) reply.send(0, result);
                        return;
                    }
                    if (capture < -1 || capture > 1) throw new IllegalArgumentException("Invalid capture request");
                    if (capture == 1) {
                        Bundle workspace = WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
                        if (mode != 2 || pause != -1 || state.getAsInt() < 2
                                || workspace == null || !workspace.getBoolean("enabled")
                                || workspace.getBoolean("locked") || workspace.getBoolean("lock_task")
                                || Settings.Global.getInt(context.getContentResolver(),SAFE,0)!=0) {
                            throw new IllegalStateException("Selection capture unavailable");
                        }
                        windows.setZetaWorkspaceSwitching(true);
                        worker.removeCallbacks(expired);worker.postDelayed(expired,10000);
                    }
                    if (capture == 0) windows.setZetaWorkspaceSwitching(false);
                    if(intent.getBooleanExtra("query",false)) {
                        if(pause!=-1 || mode!=2)throw new IllegalArgumentException("Invalid status request");
                        result.putBoolean("safe",Settings.Global.getInt(context.getContentResolver(),SAFE,0)!=0);
                        result.putInt("mode",applied);
                        if(reply!=null)reply.send(0,result);
                        return;
                    }
                    if (pause >= 0 && !Settings.Global.putInt(context.getContentResolver(), SAFE, pause)) throw new IllegalStateException("Cannot persist panel safe mode");
                    boolean safe = Settings.Global.getInt(context.getContentResolver(), SAFE, 0) != 0;
                    int base = state.getAsInt();
                    if (mode != 2 && (safe || (mode == 1 ? base != 2 : base != 3))) {
                        result.putBoolean("stale",true);
                        throw new IllegalStateException("Stale or paused single-panel request");
                    }
                    apply(mode);
                    if (capture == 1) { worker.removeCallbacks(expired); worker.postDelayed(expired,10000); }
                    result.putBoolean("safe", safe);result.putInt("mode", mode);
                    if (reply != null) reply.send(0, result);
                } catch (Exception error) {
                    result.putString("error", error.toString());
                    Slog.e("ZetaViewport", "Request failed", error);
                    if (reply != null) reply.send(1, result);
                }
            }
        },new IntentFilter(ACTION),PERMISSION,worker,Context.RECEIVER_EXPORTED);
        worker.post(() -> {
            try { apply(2); } catch (Exception error) { Slog.e("ZetaViewport", "Boot restore", error); }
        });
    }
    private void apply(int mode) throws Exception {
        IWindowManager wm = WindowManagerGlobal.getWindowManagerService();
        DisplayManagerInternal display = LocalServices.getService(DisplayManagerInternal.class);
        if (wm == null || display == null) throw new IllegalStateException("Display services not ready");
        if (mode != 2) {
            worker.removeCallbacks(expired);worker.postDelayed(expired,10000);
            if (applied == mode) return;
        }
        WindowManagerInternal windows = LocalServices.getService(WindowManagerInternal.class);
        if (windows != null) windows.setZetaWorkspaceComposition(mode);
        String saved = Settings.Global.getString(context.getContentResolver(),BASELINE);
        if (mode == 2) {
            if (saved != null) {
                String[] values = saved.split(",");
                int width=0,height=0;boolean valid=false;
                try {
                    width=Integer.parseInt(values[0]);height=Integer.parseInt(values[1]);
                    valid=values.length==3 && width>=200 && height>=200 && width<=8192 && height<=8192;
                } catch (RuntimeException malformed) { Slog.e("ZetaViewport","Invalid baseline; restoring physical size",malformed); }
                if (valid && "1".equals(values[2])) wm.setForcedDisplaySize(0,width,height);
                else wm.clearForcedDisplaySize(0);
            }
            display.setDisplayOffsets(0,0,0);
            Settings.Global.putString(context.getContentResolver(),BASELINE,null);
            worker.removeCallbacks(expired);
        } else {
            Point initial = new Point();wm.getInitialDisplaySize(0,initial);
            if (initial.x != 2754 || initial.y != 1892) throw new IllegalStateException("Unexpected physical display geometry: "+initial);
            if (saved == null) {
                Point base = new Point();wm.getBaseDisplaySize(0,base);
                saved = base.x+","+base.y+","+(base.equals(initial)?"0":"1");
                if (!Settings.Global.putString(context.getContentResolver(),BASELINE,saved)) throw new IllegalStateException("Cannot save viewport baseline");
            }
            wm.setForcedDisplaySize(0,1344,1892);
            display.setDisplayOffsets(0,mode == 0 ? -705 : 705,0);
            worker.postDelayed(expired,10000);
        }
        applied = mode;
        Slog.i("ZetaViewport","composition="+mode+" viewport="+(mode==2?"baseline":"1344x1892"));
    }
}
