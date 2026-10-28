// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
public final class EmergencyActivity extends Activity{
    @Override public void onCreate(Bundle state){
        super.onCreate(state);TextView text=new TextView(this);text.setTextSize(22);text.setPadding(48,96,48,48);text.setText("Restoring both screens...");setContentView(text);
        new Thread(()->{boolean ok=Recovery.restore(this,true);runOnUiThread(()->text.setText(ok?"Both screens restored. Automatic switching paused.":"Restoration needs attention. Keep the phone connected."));},"ZetaEmergency").start();
    }
}
