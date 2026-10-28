// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.content.Context;
import android.util.Slog;
import org.lineageos.zeta.posture.PostureContract;
final class Recovery {
    static boolean restore(Context context,boolean pause) {
        if(android.os.UserHandle.myUserId()!=0 || !context.getPackageManager().hasSystemFeature(PostureContract.FEATURE,1))return false;
        boolean viewport=false,hardware=false;
        try{ViewportClient.request(context,2,pause?1:-1);viewport=true;}catch(Exception e){Slog.e("ZetaPosture","Viewport recovery",e);}
        try{new SurfaceHardware(context).restoreBoth();hardware=true;}catch(Exception e){Slog.e("ZetaPosture","HAL recovery",e);}
        if(viewport&&hardware)try{ViewportClient.clearCapture(context);}catch(Exception error){return false;}
        return viewport&&hardware;
    }
    private Recovery(){}
}
