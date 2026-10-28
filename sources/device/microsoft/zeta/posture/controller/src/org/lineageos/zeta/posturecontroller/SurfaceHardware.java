// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.content.Context;
import android.os.PowerManager;
final class SurfaceHardware {
    private final Context context;
    private final SurfaceHalTransport transport = new SurfaceHalTransport();
    SurfaceHardware(Context context){this.context=context;}
    int composition() throws Exception {return transport.composition();}
    void displayMode(int mode) throws Exception {
        if(mode<0 || mode>2)throw new IllegalArgumentException("Unsupported composition");
        int status=transport.displayMode(mode);
        if(status!=0)throw new IllegalStateException("Display status="+status);
        if(composition()!=mode)throw new IllegalStateException("Display readback mismatch");
    }
    void touchMode(int mode) throws Exception {transport.touchMode(mode);}
    void interactive(boolean reset) throws Exception {
        SurfaceHalTransport value=transport;
        if(reset){value.interactive(true);value.interactive(false);}
        value.interactive(context.getSystemService(PowerManager.class).isInteractive());
    }
    void pingTouch() throws Exception {transport.pingTouch();}
    void restoreBoth() throws Exception {
        Exception failure=null;int before=-1;
        try {before=composition();displayMode(2);}catch(Exception error){failure=error;}
        try {touchMode(2);interactive(before==0 || before==-1);}catch(Exception error){if(failure==null)failure=error;}
        if(failure!=null)throw failure;
    }
}
