// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
public final class SafeRestoreReceiver extends BroadcastReceiver{
    @Override public void onReceive(Context context,Intent intent){
        PendingResult result=goAsync();new Thread(()->{try{Recovery.restore(context,true);}finally{result.finish();}},"ZetaLeaseRestore").start();
    }
}
