// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
public final class ControlActivity extends Activity{
    private final android.os.Handler updates=new android.os.Handler();
    private TextView status;
    private final Runnable refresh=new Runnable(){public void run(){status.setText(((ControllerApp)getApplication()).status());updates.postDelayed(this,1000);}};
    @Override protected void onResume(){super.onResume();updates.post(refresh);}
    @Override protected void onPause(){updates.removeCallbacks(refresh);super.onPause();}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);ControllerApp app=(ControllerApp)getApplication();
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(48,96,48,48);
        status=new TextView(this);status.setTextSize(22);status.setText(app.status());layout.addView(status);
        Button both=new Button(this);both.setText("Use both screens");both.setOnClickListener(v->{app.setPaused(true);status.setText("Restoring both screens...");});layout.addView(both);
        Button resume=new Button(this);resume.setText("Resume automatic switching");resume.setOnClickListener(v->{app.setPaused(false);status.setText("Resuming automatic switching...");});layout.addView(resume);setContentView(layout);
    }
}
