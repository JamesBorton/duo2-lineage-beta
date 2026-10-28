// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import static org.junit.Assert.*;
import android.os.HwBinder;
import android.os.IHwBinder;
import android.os.RemoteException;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import java.util.ArrayList;
import java.util.List;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public final class SurfaceHalTransportTest {
    @Test public void protocolRequestsHaveRequiredTypesTokensAndFlags()throws Exception {
        List<SurfaceHalTransport.Request> calls=new ArrayList<>();
        SurfaceHalTransport client=new SurfaceHalTransport(call->{calls.add(call);return 2;});
        assertEquals(2,client.composition());
        SurfaceHalTransport.Request call=calls.remove(0);
        assertEquals(SurfaceHalTransport.DISPLAY,call.service);assertEquals(call.service,call.token);
        assertEquals(2,call.code);assertEquals(0,call.flags);assertTrue(call.integerResult);
        assertEquals(SurfaceHalTransport.Argument.NONE,call.argument);
        for(int mode=0;mode<=2;mode++){
            assertEquals(2,client.displayMode(mode));call=calls.remove(0);
            assertEquals(1,call.code);assertEquals(mode,call.value);assertEquals(0,call.flags);
            assertEquals(SurfaceHalTransport.Argument.INTEGER,call.argument);assertTrue(call.integerResult);
            assertEquals(SurfaceHalTransport.DISPLAY,call.service);assertEquals(call.service,call.token);
            client.touchMode(mode);call=calls.remove(0);
            assertEquals(1,call.code);assertEquals(mode,call.value);assertEquals(1,call.flags);
            assertEquals(SurfaceHalTransport.Argument.INTEGER,call.argument);assertFalse(call.integerResult);
            assertEquals(SurfaceHalTransport.TOUCH,call.service);assertEquals(call.service,call.token);
        }
        for(boolean state:new boolean[]{true,false}){
            client.interactive(state);call=calls.remove(0);
            assertEquals(4,call.code);assertEquals(1,call.flags);assertEquals(state?1:0,call.value);
            assertEquals(SurfaceHalTransport.Argument.BOOLEAN,call.argument);assertFalse(call.integerResult);
            assertEquals(SurfaceHalTransport.TOUCH,call.service);assertEquals(call.service,call.token);
        }
        client.pingTouch();call=calls.remove(0);
        assertEquals(256921159,call.code);assertEquals(0,call.flags);
        assertEquals(SurfaceHalTransport.TOUCH,call.service);assertEquals(SurfaceHalTransport.BASE,call.token);
        assertEquals(SurfaceHalTransport.Argument.NONE,call.argument);assertFalse(call.integerResult);
    }
    @Test public void invalidRequestsAndFailuresDoNotProceedSilently()throws Exception {
        List<SurfaceHalTransport.Request> calls=new ArrayList<>();
        SurfaceHalTransport client=new SurfaceHalTransport(call->{calls.add(call);return -1;});
        for(int mode:new int[]{-1,3,Integer.MAX_VALUE}){
            try{client.displayMode(mode);fail("Invalid display mode");}catch(IllegalArgumentException expected){}
            try{client.touchMode(mode);fail("Invalid touch mode");}catch(IllegalArgumentException expected){}
        }
        assertTrue(calls.isEmpty());assertEquals(-1,client.displayMode(1));
        SurfaceHalTransport broken=new SurfaceHalTransport(call->{throw new RemoteException("test");});
        try{broken.composition();fail("Transport failure ignored");}catch(RemoteException expected){}
        SurfaceHalTransport absent=new SurfaceHalTransport(new SurfaceHalTransport.NativeDriver(descriptor->null));
        try{absent.composition();fail("Missing service ignored");}catch(IllegalStateException expected){}
    }
    @Test public void nativeParcelPingUsesRealAospServiceManagerOnly()throws Exception {
        IHwBinder manager=HwBinder.getService("android.hidl.manager@1.2::IServiceManager","default",false);
        assertNotNull(manager);
        // AOSP may supply its official local HwNoService when HIDL is absent.
        // Never create a vendor-looking local binder or register a fake service.
        new SurfaceHalTransport(new SurfaceHalTransport.NativeDriver(descriptor->manager)).pingTouch();
    }
}
