// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
/** Android-free transaction ordering/failure model, covered by host fault injection. */
final class PanelTransition {
    static final class Cancelled extends Exception { Cancelled(String why){super(why);} }
    interface Ports {
        void viewport(int mode)throws Exception;
        int current()throws Exception;
        void display(int mode)throws Exception;
        void touch(int mode)throws Exception;
        void interactive(boolean reset)throws Exception;
        boolean stillCurrent();
        void restoreViewport(boolean pause)throws Exception;
    }
    static void apply(Ports ports,int mode)throws Exception {
        if(mode<0 || mode>2)throw new IllegalArgumentException("Unknown panel mode");
        int before=-1;
        try {
            before=ports.current();
            ports.viewport(mode);
            if(!ports.stillCurrent())throw new Cancelled("Posture changed during transition");
            ports.display(mode);ports.touch(mode);ports.interactive(before==0 && mode!=0);
        }catch(Exception original){
            // Try every recovery leg even if one service is unavailable.
            try{ports.restoreViewport(!(original instanceof Cancelled));}catch(Exception e){original.addSuppressed(e);}
            try{ports.display(2);}catch(Exception e){original.addSuppressed(e);}
            try{ports.touch(2);}catch(Exception e){original.addSuppressed(e);}
            try{ports.interactive(before==0 || before==-1);}catch(Exception e){original.addSuppressed(e);}
            throw original;
        }
    }
    private PanelTransition(){}
}
