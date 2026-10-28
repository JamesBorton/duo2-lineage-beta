// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;

import android.content.Context;
import android.content.BroadcastReceiver;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.hardware.devicestate.DeviceState;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemProperties;
import android.database.ContentObserver;
import android.provider.Settings;
import android.util.Slog;
import com.android.server.devicestate.DeviceStatePolicy;
import com.android.server.devicestate.DeviceStateProvider;
import java.io.PrintWriter;
import java.util.Set;

/** OEM extension: sensor-backed close/open states, leaving power changes to DisplayManager. */
public final class ZetaDeviceStatePolicy extends DeviceStatePolicy {
    private final StateProvider provider;

    public ZetaDeviceStatePolicy(Context context) {
        super(context);
        provider = new StateProvider(context);
    }
    public static final class Provider implements DeviceStatePolicy.Provider {
        public Provider() { }
        @Override public DeviceStatePolicy instantiate(Context context) {
            return new ZetaDeviceStatePolicy(context);
        }
    }
    @Override public DeviceStateProvider getDeviceStateProvider() { return provider; }
    @Override public void configureDeviceForState(int state, Runnable onComplete) {
        // Platform app performs coordinated HAL/viewport changes after state commitment.
        onComplete.run();
    }
    @Override public void dump(PrintWriter writer, String[] args) { provider.dump(writer, args); }

    private static final class StateProvider implements DeviceStateProvider, SensorEventListener {
        private static final String TAG = "ZetaDeviceState";
        private static final int HALL_TYPE = 33171002;
        private final Context context;
        private final SensorManager manager;
        private boolean bootCompleted;
        private final Handler handler = new Handler(Looper.getMainLooper());
        private final PostureClassifier classifier = new PostureClassifier();
        private Listener listener;
        private Sensor hingeSensor;
        private Sensor hallSensor;
        private Sensor postureSensor;
        private int posture = -1;
        private int manualSide = -1;
        private float[] postureValues = new float[0];
        private final PanelViewportBridge viewport;
        private int pendingSingle = -1;
        private final Runnable commitSingle = () -> {
            int desired = desiredState();
            if (desired == pendingSingle) report(desired);
            pendingSingle = -1;
        };
        private volatile int state = PostureClassifier.OPEN;
        private boolean closePending;
        private final Runnable commitClose = () -> {
            closePending = false;
            if (bootCompleted && classifier.evaluate(state) == PostureClassifier.CLOSED) report(PostureClassifier.CLOSED);
        };

        StateProvider(Context context) {
            this.context = context;
            manager = context.getSystemService(SensorManager.class);
            viewport = new PanelViewportBridge(context, () -> state, side -> {
                java.util.concurrent.atomic.AtomicBoolean accepted = new java.util.concurrent.atomic.AtomicBoolean();
                handler.runWithScissors(() -> {
                    if (side >= 0 && side <= 1
                            && !context.getSystemService(android.app.KeyguardManager.class).isKeyguardLocked()
                            && context.getSystemService(android.os.PowerManager.class).isInteractive()
                            && classifier.hasSensors() && classifier.getHinge() >= 300
                            && classifier.evaluate(state) != PostureClassifier.CLOSED
                            && Settings.Global.getInt(context.getContentResolver(), PanelViewportBridge.SAFE, 0) == 0) {
                        manualSide = side;
                        handler.removeCallbacks(commitSingle); pendingSingle = -1;
                        report(side == 0 ? 3 : 2); accepted.set(true);
                    }
                }, 1000);
                return accepted.get();
            });
        }

        @Override public void setListener(Listener value) {
            if (listener != null) throw new IllegalStateException("Listener already set");
            listener = value;
            DeviceState closed = new DeviceState(new DeviceState.Configuration.Builder(0, "CLOSED")
                    .setPhysicalProperties(Set.of(DeviceState.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_CLOSED))
                    .setSystemProperties(Set.of(DeviceState.PROPERTY_POLICY_CANCEL_OVERRIDE_REQUESTS,
                            DeviceState.PROPERTY_POWER_CONFIGURATION_TRIGGER_SLEEP)).build());
            DeviceState open = new DeviceState(new DeviceState.Configuration.Builder(1, "OPEN")
                    .setPhysicalProperties(Set.of(DeviceState.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN))
                    .setSystemProperties(Set.of(DeviceState.PROPERTY_POWER_CONFIGURATION_TRIGGER_WAKE)).build());
            DeviceState right = new DeviceState(new DeviceState.Configuration.Builder(2,"SINGLE_RIGHT")
                    .setPhysicalProperties(Set.of(DeviceState.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN))
                    .setSystemProperties(Set.of(DeviceState.PROPERTY_POWER_CONFIGURATION_TRIGGER_WAKE)).build());
            DeviceState left = new DeviceState(new DeviceState.Configuration.Builder(3,"SINGLE_LEFT")
                    .setPhysicalProperties(Set.of(DeviceState.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN))
                    .setSystemProperties(Set.of(DeviceState.PROPERTY_POWER_CONFIGURATION_TRIGGER_WAKE)).build());
            listener.onSupportedDeviceStatesChanged(new DeviceState[]{closed, open, right, left},
                    SUPPORTED_DEVICE_STATES_CHANGED_INITIALIZED);
            listener.onStateChanged(state);
        }

        @Override public void onSystemReady() {
            handler.post(() -> {
                viewport.start();
                context.getContentResolver().registerContentObserver(Settings.Global.getUriFor(PanelViewportBridge.SAFE),
                        false,new ContentObserver(handler) { @Override public void onChange(boolean self) { updateState(); } });
                // DisplayManager suppresses fold sleep before boot completion. Keep OPEN until
                // then, so booting while closed still gets a real post-boot CLOSED transition.
                bootCompleted = SystemProperties.getBoolean("sys.boot_completed", false);
                if (!bootCompleted) {
                    BroadcastReceiver receiver = new BroadcastReceiver() {
                        @Override public void onReceive(Context ignored, Intent intent) {
                            context.unregisterReceiver(this);
                            handler.post(() -> { bootCompleted = true; updateState(); });
                        }
                    };
                    context.registerReceiver(receiver, new IntentFilter(Intent.ACTION_BOOT_COMPLETED),
                            Context.RECEIVER_NOT_EXPORTED);
                    // Avoid losing a completion which raced receiver registration.
                    bootCompleted = SystemProperties.getBoolean("sys.boot_completed", false);
                }
                registerSensors();
            });
        }

        private Sensor findWakeup(int type, String name) {
            if (manager == null) return null;
            for (Sensor sensor : manager.getSensorList(type)) {
                if (sensor.isWakeUpSensor() && name.equals(sensor.getName())) return sensor;
            }
            return null;
        }
        private void registerSensors() {
            // Only use the exact wakeup variants proven in the physical capture.
            hingeSensor = findWakeup(Sensor.TYPE_HINGE_ANGLE, "Surface Hinge Angle Wakeup");
            hallSensor = findWakeup(HALL_TYPE, "Surface Hall 0 Wakeup");
            if (hingeSensor == null || hallSensor == null) {
                Slog.e(TAG, "Required wakeup sensors missing; retaining OPEN");
                return;
            }
            boolean hingeOk = manager.registerListener(this, hingeSensor, SensorManager.SENSOR_DELAY_NORMAL, handler);
            boolean hallOk = manager.registerListener(this, hallSensor, SensorManager.SENSOR_DELAY_NORMAL, handler);
            classifier.setSensorsAvailable(hingeOk && hallOk);
            if (!classifier.hasSensors()) {
                manager.unregisterListener(this);
                Slog.e(TAG, "Sensor registration failed; retaining OPEN");
                return;
            }
            for (Sensor sensor : manager.getSensorList(33171009)) {
                if (!sensor.isWakeUpSensor() && "Surface Posture Non-wakeup".equals(sensor.getName())) {
                    try {
                        if (manager.registerListener(this,sensor,SensorManager.SENSOR_DELAY_NORMAL,handler)) postureSensor=sensor;
                    } catch (SecurityException error) { Slog.e(TAG,"Protected posture unavailable; keeping dual mode",error); }
                    break;
                }
            }
        }
        @Override public void onSensorChanged(SensorEvent event) {
            if (event.values.length == 0) return;
            if (event.sensor == hingeSensor) {
                classifier.setHinge(event.values[0]);
                if (event.values[0] <= 260) { posture = -1; manualSide = -1; } // do not reuse a stale side on the next fold
            }
            else if (event.sensor == hallSensor) classifier.setHall(event.values[0]);
            else if (event.sensor == postureSensor) {
                postureValues=event.values.clone();
                float value=event.values[0];
                posture=Float.isFinite(value) && value>=0 && value<=16 && value==(int)value ? (int)value : -1;
            }
            else return;
            updateState();
        }
        private int desiredState() {
            int result = NativeStatePlanner.desired(bootCompleted,
                    Settings.Global.getInt(context.getContentResolver(),PanelViewportBridge.SAFE,0)!=0,
                    classifier,posture,state);
            return result >= 2 && manualSide >= 0 ? (manualSide == 0 ? 3 : 2) : result;
        }
        private void updateState() {
            int desired = desiredState();
            if (desired < 2) { handler.removeCallbacks(commitSingle);pendingSingle=-1; }
            if (desired >= 2 && desired != state) {
                handler.removeCallbacks(commitClose);closePending=false;
                if (pendingSingle!=desired) {
                    handler.removeCallbacks(commitSingle);pendingSingle=desired;handler.postDelayed(commitSingle,150);
                }
                return;
            }
            if (desired == PostureClassifier.CLOSED && state != desired) {
                if (!closePending) { closePending = true; handler.postDelayed(commitClose, 100); }
            } else {
                handler.removeCallbacks(commitClose);
                closePending = false;
                report(desired);
            }
        }
        private void report(int desired) {
            if (state == desired) return;
            state = desired;
            Slog.i(TAG, "state=" + state + " hinge=" + classifier.getHinge() + " hall0=" + classifier.getHall());
            if (listener != null) listener.onStateChanged(state);
        }
        @Override public void onAccuracyChanged(Sensor sensor, int accuracy) {
            if (sensor==postureSensor && accuracy==SensorManager.SENSOR_STATUS_UNRELIABLE) { posture=-1;updateState(); }
        }
        @Override public void dump(PrintWriter writer, String[] args) {
            writer.println("Zeta closed/open state=" + state + " sensorsAvailable=" + classifier.hasSensors()
                    + " hinge=" + classifier.getHinge() + " hall0=" + classifier.getHall()
                    + " closePending=" + closePending + " bootCompleted=" + bootCompleted);
            writer.println("postureValues="+java.util.Arrays.toString(postureValues));
            writer.println("posture="+posture+" privateSensor="+(postureSensor!=null)+" manualSide="+manualSide+" pendingSingle="+pendingSingle);
        }
    }
}
