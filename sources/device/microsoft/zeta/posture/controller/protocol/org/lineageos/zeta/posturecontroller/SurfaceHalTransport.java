// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 James Borton and the project contributors.
package org.lineageos.zeta.posturecontroller;
import android.os.HwBinder;
import android.os.HwParcel;
import android.os.IHwBinder;
import android.os.RemoteException;

/** Narrow panel client over AOSP transport; no generated vendor classes. */
final class SurfaceHalTransport {
    static final String DISPLAY="vendor.surface.displaytopology@1.0::IDisplayTopology";
    static final String TOUCH="vendor.surface.touchpen@1.0::ITouchPen";
    static final String BASE="android.hidl.base@1.0::IBase";
    static final int ONEWAY=1;
    enum Argument { NONE, INTEGER, BOOLEAN }
    static final class Request {
        final String service,token;
        final int code,flags,value;
        final Argument argument;
        final boolean integerResult;
        Request(String service,String token,int code,int flags,Argument argument,int value,boolean integerResult) {
            this.service=service;this.token=token;this.code=code;this.flags=flags;
            this.argument=argument;this.value=value;this.integerResult=integerResult;
        }
    }
    interface Driver { int exchange(Request call) throws RemoteException; }
    interface Lookup { IHwBinder find(String descriptor) throws RemoteException; }
    static final class NativeDriver implements Driver {
        private final Lookup lookup;
        NativeDriver(){this(descriptor -> HwBinder.getService(descriptor,"default",false));}
        NativeDriver(Lookup lookup){this.lookup=lookup;}
        @Override public int exchange(Request call)throws RemoteException {
            IHwBinder remote=lookup.find(call.service);
            if(remote==null)throw new IllegalStateException("Required panel service unavailable");
            HwParcel request=new HwParcel(),reply=new HwParcel();
            try {
                request.writeInterfaceToken(call.token);
                switch(call.argument){
                    case INTEGER:request.writeInt32(call.value);break;
                    case BOOLEAN:request.writeBool(call.value!=0);break;
                    case NONE:break;
                }
                remote.transact(call.code,request,reply,call.flags);
                if((call.flags&ONEWAY)!=0)return 0;
                reply.verifySuccess();
                return call.integerResult?reply.readInt32():0;
            }finally{request.releaseTemporaryStorage();reply.release();}
        }
    }
    private final Driver driver;
    SurfaceHalTransport(){this(new NativeDriver());}
    SurfaceHalTransport(Driver driver){this.driver=driver;}
    private static void checkMode(int mode){if(mode<0||mode>2)throw new IllegalArgumentException("Unsupported panel mode");}
    int composition()throws RemoteException{return driver.exchange(new Request(DISPLAY,DISPLAY,2,0,Argument.NONE,0,true));}
    int displayMode(int mode)throws RemoteException{checkMode(mode);return driver.exchange(new Request(DISPLAY,DISPLAY,1,0,Argument.INTEGER,mode,true));}
    void touchMode(int mode)throws RemoteException{checkMode(mode);driver.exchange(new Request(TOUCH,TOUCH,1,ONEWAY,Argument.INTEGER,mode,false));}
    void interactive(boolean enabled)throws RemoteException{driver.exchange(new Request(TOUCH,TOUCH,4,ONEWAY,Argument.BOOLEAN,enabled?1:0,false));}
    void pingTouch()throws RemoteException{driver.exchange(new Request(TOUCH,BASE,256921159,0,Argument.NONE,0,false));}
}
