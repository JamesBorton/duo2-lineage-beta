// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacepermissiontests;

import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.MotionEvent;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;
import static org.junit.Assume.assumeTrue;

/** Captures held input positions, not assumed animation-progress percentages. QEMU only. */
public class PreviewGeometryTest {
    @Test public void captureHeldSwipe() throws Exception {
        Bundle args = InstrumentationRegistry.getArguments();
        assumeTrue(args.containsKey("zeta_case"));
        assertEquals("lineage_zeta_workspace_emu", android.os.SystemProperties.get("ro.product.name"));
        assertTrue(android.os.SystemProperties.getBoolean("ro.boot.qemu", false)
                || android.os.SystemProperties.getBoolean("ro.kernel.qemu", false));
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        int panel = Integer.parseInt(args.getString("zeta_panel", "1"));
        assertTrue(panel == 0 || panel == 1);
        float x = Float.parseFloat(args.getString("zeta_x", panel == 0 ? "672" : "2082"));
        float startY = Float.parseFloat(args.getString("zeta_start_y", "1838"));
        float endY = Float.parseFloat(args.getString("zeta_end_y", "1149"));
        String name = args.getString("zeta_case", "right-1838");
        assertTrue(name.matches("[a-z0-9-]{1,48}"));
        UiAutomation automation = instrumentation.getUiAutomation();
        automation.adoptShellPermissionIdentity(android.Manifest.permission.MANAGE_ACTIVITY_TASKS);
        File directory = new File(instrumentation.getContext().getCacheDir(), name);
        assertTrue(directory.mkdir() || directory.isDirectory());
        long down = 0;
        float y = startY;
        boolean pressed = false;
        try {
            Bundle state = android.view.WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
            assertTrue(state.getBoolean("enabled"));
            assertFalse(state.getBoolean("locked"));
            assertEquals(2, state.getInt("composition"));
            assertEquals(Integer.parseInt(args.getString("zeta_rotation", "0")),
                    instrumentation.getContext().getSystemService(android.hardware.display.DisplayManager.class)
                    .getDisplay(android.view.Display.DEFAULT_DISPLAY).getRotation());
            capture(automation, directory, "before", panel, 0, x, y, false);
            down = SystemClock.uptimeMillis();
            event(automation, down, MotionEvent.ACTION_DOWN, x, y);
            pressed = true;
            for (int step = 1; step <= 40; step++) {
                SystemClock.sleep(16);
                y = startY + (endY - startY) * step / 40f;
                event(automation, down, MotionEvent.ACTION_MOVE, x, y);
                if (step % 10 == 0) {
                    SystemClock.sleep(120);
                    capture(automation, directory, "input-" + step, panel, down, x, y, true);
                }
            }
            SystemClock.sleep(700);
            capture(automation, directory, "hold", panel, down, x, y, true);
            Bundle status = new Bundle(); status.putString("stream", "ZETA_PREVIEW_HOLD " + name + "\n");
            instrumentation.sendStatus(1, status);
            SystemClock.sleep(1500);
            event(automation, down, "true".equals(args.getString("zeta_cancel"))
                    ? MotionEvent.ACTION_CANCEL : MotionEvent.ACTION_UP, x, y);
            pressed = false;
            SystemClock.sleep(1000);
            capture(automation, directory, "settled", panel, down, x, y, false);
        } finally {
            if (pressed) event(automation, down, MotionEvent.ACTION_CANCEL, x, y);
            automation.dropShellPermissionIdentity();
        }
    }

    private static void event(UiAutomation automation, long down, int action, float x, float y) {
        MotionEvent event = MotionEvent.obtain(down, SystemClock.uptimeMillis(), action, x, y, 0);
        event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
        try { assertTrue(automation.injectInputEvent(event, true, false)); }
        finally { event.recycle(); }
    }


    private static JSONObject measureMarkers(Bitmap bitmap, android.graphics.Rect[] panes) throws Exception {
        int width = bitmap.getWidth(), height = bitmap.getHeight();
        int[] pixels = new int[width * height];
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height);
        int[] counts = new int[2];
        int[][] paneCounts = new int[2][2];
        int[] left = {width, width}, top = {height, height}, right = {0, 0}, bottom = {0, 0};
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            int rgb = pixels[y * width + x];
            int r = (rgb >> 16) & 255, g = (rgb >> 8) & 255, b = rgb & 255;
            // Hue ratios tolerate uniform transition dimming, not arbitrary pixel changes.
            int kind = r >= 50 && b >= 60 && g < r * .4f && Math.abs(211*r - 173*b) < 8*211 ? 1
                    : g >= 60 && r < g * .4f && Math.abs(79*g - 173*b) < 8*173 ? 0 : -1;
            if (kind < 0) continue;
            if (panes[0].contains(x, y)) paneCounts[kind][0]++;
            else if (panes[1].contains(x, y)) paneCounts[kind][1]++;
            counts[kind]++; left[kind] = Math.min(left[kind], x); top[kind] = Math.min(top[kind], y);
            right[kind] = Math.max(right[kind], x+1); bottom[kind] = Math.max(bottom[kind], y+1);
        }
        JSONObject result = new JSONObject();
        for (int kind = 0; kind < 2; kind++) {
            result.put(kind == 0 ? "left_fixture" : "right_fixture", new JSONObject()
                    .put("pixels", counts[kind]).put("pane_pixels", new org.json.JSONArray(paneCounts[kind]))
                    .put("bounds", new org.json.JSONArray(new int[] {
                            left[kind], top[kind], right[kind], bottom[kind]})));
        }
        return result;
    }

    private static void capture(UiAutomation automation, File directory, String label,
            int panel, long down, float x, float y, boolean pressed) throws Exception {
        Bundle state = android.view.WindowManagerGlobal.getWindowManagerService().getZetaWorkspaceState();
        android.graphics.Rect[] panes = {
            state.getParcelable("bounds_0", android.graphics.Rect.class),
            state.getParcelable("bounds_1", android.graphics.Rect.class)};
        assertNotNull(panes[0]); assertNotNull(panes[1]);
        long start = SystemClock.uptimeMillis();
        Bitmap bitmap = automation.takeScreenshot();
        assertNotNull(bitmap);
        long captured = SystemClock.uptimeMillis();
        JSONObject markers = measureMarkers(bitmap, panes);
        try (FileOutputStream output = new FileOutputStream(new File(directory, label + ".png"))) {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output));
        } finally { bitmap.recycle(); }
        android.app.ActivityManager.RunningTaskInfo task = state.getParcelable(
                "standard_taskinfo_" + panel, android.app.ActivityManager.RunningTaskInfo.class);
        JSONObject data = new JSONObject();
        data.put("markers", markers).put("label", label).put("capture_start_uptime_ms", start)
                .put("capture_end_uptime_ms", captured).put("down_uptime_ms", down)
                .put("input_x", x).put("input_y", y).put("pressed", pressed)
                .put("panel", panel).put("composition", state.getInt("composition"))
                .put("navigation_height", state.getInt("navigation_height"))
                .put("pane_bounds", String.valueOf(state.getParcelable("bounds_" + panel)))
                .put("task_id", task == null ? -1 : task.taskId)
                .put("task_bounds", task == null ? "none" : task.configuration.windowConfiguration.getBounds().toShortString());
        try (FileOutputStream output = new FileOutputStream(new File(directory, label + ".json"))) {
            output.write(data.toString(2).getBytes(StandardCharsets.UTF_8));
        }
    }
}
