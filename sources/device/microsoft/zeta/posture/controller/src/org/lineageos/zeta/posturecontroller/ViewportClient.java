// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Parcel;
import android.os.ResultReceiver;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.lineageos.zeta.posture.PostureContract;
final class ViewportClient {
    static boolean querySafe(Context context)throws Exception{return request(context,2,-1,true);}
    static boolean request(Context context,int mode,int pause)throws Exception{return request(context,mode,pause,false);}
    private static boolean request(Context context,int mode,int pause,boolean query) throws Exception {
        return transact(context,mode,pause,query,-1,-1);
    }
    static boolean capture(Context context)throws Exception{return transact(context,2,-1,false,1,-1);}
    static void clearCapture(Context context)throws Exception{transact(context,2,-1,true,0,-1);}
    static void select(Context context,int side)throws Exception{transact(context,2,-1,false,-1,side);}
    private static boolean transact(Context context,int mode,int pause,boolean query,int capture,int side)throws Exception {
        CountDownLatch done=new CountDownLatch(1);
        AtomicInteger code=new AtomicInteger(1);AtomicReference<Bundle> data=new AtomicReference<>();
        ResultReceiver receiver=new ResultReceiver(null) {
            @Override protected void onReceiveResult(int value,Bundle result) {
                code.set(value);data.set(result);done.countDown();
            }
        };
        // Rewrap as the framework base class so system_server need not load an app subclass.
        Parcel parcel=Parcel.obtain();receiver.writeToParcel(parcel,0);parcel.setDataPosition(0);
        ResultReceiver remote=ResultReceiver.CREATOR.createFromParcel(parcel);parcel.recycle();
        Intent request=new Intent(PostureContract.VIEWPORT).setPackage("android");
        request.addFlags(Intent.FLAG_RECEIVER_FOREGROUND);
        request.putExtra("mode",mode).putExtra("pause",pause).putExtra("query",query).putExtra("reply",remote).putExtra("capture",capture).putExtra("select",side);
        context.sendBroadcast(request);
        if(!done.await(2500,TimeUnit.MILLISECONDS))throw new IllegalStateException("Viewport acknowledgement timed out");
        Bundle result=data.get();
        if(code.get()!=0){
            if(result!=null && result.getBoolean("stale",false))throw new PanelTransition.Cancelled("Posture changed or paused");
            throw new IllegalStateException(result==null?"Viewport rejected":result.getString("error"));
        }
        return result!=null && result.getBoolean("safe",false);
    }
}
