// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.workspacetest;

import android.app.Activity;
import android.os.Bundle;
import android.view.Gravity;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.widget.EditText;

/** An editor covering both physical panes, including vertically stacked rotations. */
public class FullEditorActivity extends Activity {
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        EditText editor = new EditText(this);
        editor.setId(1001);
        editor.setGravity(Gravity.TOP | Gravity.START);
        editor.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        editor.setHint("Full-area keyboard test");
        editor.setContentDescription("workspace-input");
        editor.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });
        setContentView(editor);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
                | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    }
}
