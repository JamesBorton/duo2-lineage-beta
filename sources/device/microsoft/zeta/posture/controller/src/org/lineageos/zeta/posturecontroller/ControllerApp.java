// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import android.app.Application;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.devicestate.DeviceState;
import android.hardware.devicestate.DeviceStateManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.UserHandle;
import android.util.Slog;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.lineageos.zeta.posture.PostureContract;

public final class ControllerApp extends Application {
    private Handler worker;
    private SurfaceHardware hardware;
    private final AtomicInteger generation=new AtomicInteger();
    private volatile int desired=2;
    private volatile boolean providerOk,ready,paused;
    private int applied=-1;
    private boolean capturing;
    private android.os.IBinder captureOwner;
    private final android.os.IBinder.DeathRecipient captureDeath = () -> worker.post(() -> endCapture(-1));
    private final Runnable captureTimeout = () -> endCapture(-1);

    @Override public void onCreate(){
        super.onCreate();
        if(Application.getProcessName().endsWith(":restore") || UserHandle.myUserId()!=0)return;
        if(!getPackageManager().hasSystemFeature(PostureContract.FEATURE,1))return;
        HandlerThread thread=new HandlerThread("ZetaPanelController");thread.start();worker=new Handler(thread.getLooper());
        hardware=new SurfaceHardware(this);
        DeviceStateManager states=getSystemService(DeviceStateManager.class);
        states.registerCallback(getMainExecutor(),new DeviceStateManager.DeviceStateCallback(){
            @Override public void onSupportedStatesChanged(List<DeviceState> values){
                boolean closed=false,open=false,right=false,left=false;
                for(DeviceState value:values){
                    closed|=value.getIdentifier()==0 && "CLOSED".equals(value.getName());
                    open|=value.getIdentifier()==1 && "OPEN".equals(value.getName());
                    right|=value.getIdentifier()==2 && "SINGLE_RIGHT".equals(value.getName());
                    left|=value.getIdentifier()==3 && "SINGLE_LEFT".equals(value.getName());
                }
                providerOk=closed&&open&&right&&left;
                generation.incrementAndGet();worker.post(ControllerApp.this::applyDesired);
            }
            @Override public void onDeviceStateChanged(DeviceState value){
                desired=value.getIdentifier()==2?1:value.getIdentifier()==3?0:2;
                generation.incrementAndGet();
                boolean exit = value.getIdentifier() < 2;
                worker.post(() -> { if (capturing && exit) endCapture(-1); else applyDesired(); });
            }
        });
        registerReceiver(new BroadcastReceiver(){
            @Override public void onReceive(Context c,Intent intent){
                worker.post(()->{if(!ready)return;if(capturing)endCapture(-1);try{hardware.interactive(false);}catch(Exception e){fail(e);}});
            }
        },new IntentFilter(){ {addAction(Intent.ACTION_SCREEN_ON);addAction(Intent.ACTION_SCREEN_OFF);} },Context.RECEIVER_NOT_EXPORTED);
        registerReceiver(new BroadcastReceiver() {
            @Override public void onReceive(Context context, Intent intent) {
                android.os.ResultReceiver reply = intent.getParcelableExtra("reply", android.os.ResultReceiver.class);
                int command = intent.getIntExtra("command", -1), side = intent.getIntExtra("side", -1);
                android.os.IBinder owner = intent.getExtras() == null ? null : intent.getExtras().getBinder("owner");
                worker.post(() -> {
                    int result = 0;
                    try {
                        if (command == 0) beginCapture(owner);
                        else if (command == 1) { if (side < 0 || side > 1) throw new IllegalArgumentException(); endCapture(side); }
                        else if (command == 2) endCapture(-1);
                        else throw new IllegalArgumentException();
                    } catch (CaptureUnavailable rejected) {
                        // A fold, lock, or screen-off can win the request race. No
                        // hardware/viewport state changed; reject without pausing policy.
                        result = 1; Slog.d("ZetaPosture", "Screen selection request is no longer eligible");
                    } catch (Exception error) { result = 1; fail(error); }
                    if (reply != null) reply.send(result, new android.os.Bundle());
                });
            }
        }, new IntentFilter("org.lineageos.zeta.action.SCREEN_SELECTION"),
                PostureContract.PERMISSION, null, Context.RECEIVER_EXPORTED);
        worker.post(this::tick);
    }
    private void tick(){
        try{
            if(capturing)return;
            if(!ready){
                if(!Recovery.restore(this,false))throw new IllegalStateException("Initial restore not ready");
                paused=ViewportClient.querySafe(this);ready=true;applied=2;
                Slog.i("ZetaPosture","Controller ready; paused="+paused);
                applyDesired();
            }else if(paused && applied!=2){
                if(Recovery.restore(this,true))applied=2;
            }else if(applied!=2 && !paused){
                if(hardware.composition()!=applied)throw new IllegalStateException("HAL composition changed externally");
                hardware.pingTouch();ViewportClient.request(this,applied,-1);
            }else if(applied==2){
                paused=ViewportClient.querySafe(this);
            }
        }catch(PanelTransition.Cancelled e){
            if(Recovery.restore(this,false)){applied=2;worker.post(this::applyDesired);}
            else fail(e);
        }catch(Exception e){
            if(ready)fail(e);else Slog.w("ZetaPosture","Waiting for viewport bridge",e);
        }finally{worker.postDelayed(this::tick,2000);}
    }
    private void applyDesired(){
        if(!ready || !providerOk || capturing)return;
        final int mode=paused?2:desired;
        if(mode==applied)return;
        final int version=generation.get();
        try{
            PanelTransition.apply(new PanelTransition.Ports(){
                public void viewport(int value)throws Exception{paused=ViewportClient.request(ControllerApp.this,value,-1);}
                public int current()throws Exception{return hardware.composition();}
                public void display(int value)throws Exception{hardware.displayMode(value);}
                public void touch(int value)throws Exception{hardware.touchMode(value);}
                public void interactive(boolean reset)throws Exception{hardware.interactive(reset);}
                public boolean stillCurrent(){return generation.get()==version && (mode==2 || !paused);}
                public void restoreViewport(boolean pause)throws Exception{paused=ViewportClient.request(ControllerApp.this,2,pause?1:-1);}
            },mode);
            applied=mode;Slog.i("ZetaPosture","Applied composition="+mode);
        }catch(PanelTransition.Cancelled cancelled){
            if(cancelled.getSuppressed().length!=0)fail(cancelled);
            else{applied=2;worker.post(this::applyDesired);}
        }catch(Exception error){fail(error);}
    }
    private static final class CaptureUnavailable extends Exception { }

    private void beginCapture(android.os.IBinder owner)throws Exception {
        if (!ready || !providerOk || paused || capturing || desired == 2 || owner == null
                || !getSystemService(android.os.PowerManager.class).isInteractive()
                || getSystemService(android.app.KeyguardManager.class).isKeyguardLocked()) {
            throw new CaptureUnavailable();
        }
        try { owner.linkToDeath(captureDeath, 0); }
        catch (android.os.RemoteException deadOwner) { throw new CaptureUnavailable(); }
        captureOwner = owner;
        capturing = true; generation.incrementAndGet();
        worker.postDelayed(captureTimeout, 5000);
        ViewportClient.capture(this); // Hide app areas before restoring the full input viewport.
        hardware.restoreBoth(); applied = 2;
    }
    private void endCapture(int side) {
        if (!capturing) return;
        worker.removeCallbacks(captureTimeout);
        try {
            if (side >= 0) {
                if (getSystemService(android.app.KeyguardManager.class).isKeyguardLocked()
                        || !getSystemService(android.os.PowerManager.class).isInteractive()) {
                    throw new IllegalStateException("Selection while locked/asleep");
                }
                ViewportClient.select(this, side); desired = side;
            }
            capturing = false; applied = -1; generation.incrementAndGet();
            applyDesired();
            if (applied < 0) throw new IllegalStateException("Selection restore failed");
            ViewportClient.clearCapture(this); // Reveal only after the hardware and viewport match.
        } catch (Exception error) { fail(error); }
        finally {
            if (captureOwner != null) captureOwner.unlinkToDeath(captureDeath, 0);
            captureOwner = null;
        }
    }
    private void fail(Exception error){
        capturing=false;worker.removeCallbacks(captureTimeout);
        if(captureOwner!=null){captureOwner.unlinkToDeath(captureDeath,0);captureOwner=null;}

        paused=true;applied=-1;generation.incrementAndGet();
        Slog.e("ZetaPosture","Pausing automatic switching after error",error);
        if(Recovery.restore(this,true))applied=2;
    }
    void setPaused(boolean value){
        if(worker==null)return;
        generation.incrementAndGet();
        worker.post(()->{
            try{
                if(capturing)endCapture(-1);
                hardware.restoreBoth();ViewportClient.request(this,2,value?1:0);ViewportClient.clearCapture(this);
                paused=value;ready=true;applied=2;applyDesired();
            }catch(Exception e){fail(e);}
        });
    }
    String status(){return worker==null?"This system update is not active.":!ready?"Starting screen switching...":paused?"Both screens selected. Automatic switching paused.":"Automatic screen switching is active.";}
}
