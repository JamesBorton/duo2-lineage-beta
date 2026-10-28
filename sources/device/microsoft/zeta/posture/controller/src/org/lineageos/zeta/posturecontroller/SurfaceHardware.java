// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.content.Context;
import android.os.PowerManager;
import vendor.surface.displaytopology.V1_0.IDisplayTopology;
import vendor.surface.touchpen.V1_0.ITouchPen;
final class SurfaceHardware {
    private final Context context;
    SurfaceHardware(Context context){this.context=context;}
    private IDisplayTopology display() throws Exception {
        IDisplayTopology value=IDisplayTopology.getService(false);
        if(value==null)throw new IllegalStateException("Display HAL unavailable");return value;
    }
    private ITouchPen touch() throws Exception {
        ITouchPen value=ITouchPen.getService(false);
        if(value==null)throw new IllegalStateException("Touch HAL unavailable");return value;
    }
    int composition() throws Exception {return display().getComposition();}
    void displayMode(int mode) throws Exception {
        if(mode<0 || mode>2)throw new IllegalArgumentException("Unsupported composition");
        int status=display().setComposition(mode);
        if(status!=0)throw new IllegalStateException("Display status="+status);
        if(composition()!=mode)throw new IllegalStateException("Display readback mismatch");
    }
    void touchMode(int mode) throws Exception {touch().setDisplayState(mode);}
    void interactive(boolean reset) throws Exception {
        ITouchPen value=touch();
        if(reset){value.setInteractive(true);value.setInteractive(false);}
        value.setInteractive(context.getSystemService(PowerManager.class).isInteractive());
    }
    void pingTouch() throws Exception {touch().ping();}
    void restoreBoth() throws Exception {
        Exception failure=null;int before=-1;
        try {before=composition();displayMode(2);}catch(Exception error){failure=error;}
        try {touchMode(2);interactive(before==0 || before==-1);}catch(Exception error){if(failure==null)failure=error;}
        if(failure!=null)throw failure;
    }
}
