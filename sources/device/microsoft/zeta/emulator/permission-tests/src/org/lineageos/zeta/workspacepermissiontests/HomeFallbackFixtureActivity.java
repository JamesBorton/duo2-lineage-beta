// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacepermissiontests;

/** Unprivileged, emulator-only Home for the unsupported-launcher reboot gate. */
public final class HomeFallbackFixtureActivity extends android.app.Activity {
    @Override public void onCreate(android.os.Bundle saved) {
        super.onCreate(saved);
        android.widget.TextView text = new android.widget.TextView(this);
        text.setText("Home fallback test");
        setContentView(text);
    }
}
