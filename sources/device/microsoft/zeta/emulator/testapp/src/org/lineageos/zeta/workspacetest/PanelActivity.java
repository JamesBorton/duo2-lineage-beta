// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacetest;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Real application UI for task bounds, launch-origin, scroll and IME integration tests. */
public class PanelActivity extends Activity {
    private boolean mImmersive;
    private Object mLayoutComponent;
    private android.os.CancellationSignal mAuthCancel;
    private java.util.function.Consumer<Object> mLayoutListener;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        // Explicit synthetic marker for intermediate-frame geometry assertions.
        // Existing fixture behavior and all ordinary test runs retain their theme.
        if (getIntent().getBooleanExtra("zeta_preview_fixture", false)) {
            root.setBackgroundColor(getClass().getSimpleName().equals("RightActivity")
                    ? android.graphics.Color.rgb(173, 43, 211)
                    : android.graphics.Color.rgb(37, 173, 79));
        }
        root.setFocusableInTouchMode(true);
        TextView metrics = new TextView(this);
        metrics.setContentDescription("workspace-metrics");
        metrics.setText(getClass().getSimpleName() + " task=" + getTaskId()
                + " dp=" + getResources().getConfiguration().screenWidthDp + "x"
                + getResources().getConfiguration().screenHeightDp
                + " bounds=" + getWindowManager().getCurrentWindowMetrics().getBounds().toShortString());
        root.addView(metrics);
        TextView insetsText = new TextView(this);
        insetsText.setContentDescription("workspace-insets");
        root.addView(insetsText);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars());
            android.graphics.Insets ime = insets.getInsets(android.view.WindowInsets.Type.ime());
            insetsText.setText("ime=" + insets.isVisible(android.view.WindowInsets.Type.ime())
                    + " bottom=" + ime.bottom + " bars=" + bars
                    + " nav=" + insets.isVisible(android.view.WindowInsets.Type.navigationBars()));
            view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, ime.bottom));
            return insets;
        });
        TextView hingeText = new TextView(this);
        hingeText.setContentDescription("workspace-hinge");
        hingeText.setText("hinge pending");
        root.addView(hingeText);
        observeHinge(hingeText);
        EditText input = new EditText(this);
        input.setId(1001);
        input.setSingleLine(true);
        input.setHint("Keyboard test");
        input.setContentDescription("workspace-input");
        root.addView(input);
        Button child = new Button(this);
        child.setText("Launch child from this panel");
        child.setOnClickListener(view -> startActivity(new Intent(this, ChildActivity.class)));
        root.addView(child);
        TextView authResult = new TextView(this);
        authResult.setContentDescription("workspace-auth-result");
        root.addView(authResult);
        Button authenticate = new Button(this);
        authenticate.setText("Authenticate");
        authenticate.setOnClickListener(view -> {
            if (mAuthCancel != null) mAuthCancel.cancel();
            mAuthCancel = new android.os.CancellationSignal();
            new android.hardware.biometrics.BiometricPrompt.Builder(this)
                    .setTitle("Workspace credential test")
                    .setAllowedAuthenticators(android.hardware.biometrics.BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                    .build().authenticate(mAuthCancel, getMainExecutor(),
                            new android.hardware.biometrics.BiometricPrompt.AuthenticationCallback() {
                                @Override public void onAuthenticationSucceeded(
                                        android.hardware.biometrics.BiometricPrompt.AuthenticationResult result) {
                                    authResult.setText("authenticated");
                                }
                                @Override public void onAuthenticationError(int code, CharSequence message) {
                                    authResult.setText("auth-error " + code);
                                }
                            });
        });
        root.addView(authenticate);
        Button immersive = new Button(this);
        immersive.setText("Immersive enable");
        immersive.setContentDescription("workspace-immersive");
        immersive.setOnClickListener(view -> {
            mImmersive = !mImmersive;
            android.view.WindowInsetsController controller = getWindow().getInsetsController();
            controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            if (mImmersive) controller.hide(android.view.WindowInsets.Type.systemBars());
            else controller.show(android.view.WindowInsets.Type.systemBars());
            immersive.setText(mImmersive ? "Immersive disable" : "Immersive enable");
        });
        root.addView(immersive);
        ScrollView scroll = new ScrollView(this);
        scroll.setId(1002);
        scroll.setContentDescription("workspace-scroll");
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        for (int i = 0; i < 200; i++) {
            TextView row = new TextView(this);
            row.setText(getClass().getSimpleName() + " row " + i);
            row.setTextSize(24);
            row.setPadding(12, 12, 12, 12);
            rows.addView(row);
        }
        scroll.addView(rows);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        root.requestFocus();
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_UNSPECIFIED
                | android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    }

    // The extension is an optional public OEM library, not a hidden framework API.
    private void observeHinge(TextView label) {
        try {
            Class<?> provider = Class.forName("androidx.window.extensions.WindowExtensionsProvider");
            Object extensions = provider.getMethod("getWindowExtensions").invoke(null);
            mLayoutComponent = Class.forName("androidx.window.extensions.WindowExtensions")
                    .getMethod("getWindowLayoutComponent").invoke(extensions);
            if (mLayoutComponent == null) throw new IllegalStateException("No layout component");
            mLayoutListener = info -> runOnUiThread(() -> {
                try {
                    java.util.List<?> features = (java.util.List<?>) info.getClass()
                            .getMethod("getDisplayFeatures").invoke(info);
                    StringBuilder text = new StringBuilder("hinge count=" + features.size());
                    for (Object feature : features) {
                        android.graphics.Rect bounds = (android.graphics.Rect) feature.getClass()
                                .getMethod("getBounds").invoke(feature);
                        text.append(" bounds=").append(bounds.toShortString())
                                .append(" type=").append(feature.getClass().getMethod("getType").invoke(feature));
                    }
                    label.setText(text);
                } catch (ReflectiveOperationException error) { label.setText("hinge error=" + error); }
            });
            Class.forName("androidx.window.extensions.layout.WindowLayoutComponent")
                    .getMethod("addWindowLayoutInfoListener", Activity.class, java.util.function.Consumer.class)
                    .invoke(mLayoutComponent, this, mLayoutListener);
        } catch (ReflectiveOperationException | RuntimeException error) {
            label.setText("hinge unavailable=" + error.getClass().getSimpleName());
        }
    }
    @Override protected void onDestroy() {
        if (mAuthCancel != null) mAuthCancel.cancel();
        if (mLayoutComponent != null && mLayoutListener != null) {
            try {
                Class.forName("androidx.window.extensions.layout.WindowLayoutComponent")
                        .getMethod("removeWindowLayoutInfoListener", java.util.function.Consumer.class)
                        .invoke(mLayoutComponent, mLayoutListener);
            } catch (ReflectiveOperationException ignored) { }
        }
        super.onDestroy();
    }
}
