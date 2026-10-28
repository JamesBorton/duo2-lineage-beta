// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;

/** Sensor-only decision model. Missing or invalid data leaves the display usable. */
public final class PostureClassifier {
    public static final int CLOSED = 0;
    public static final int OPEN = 1;
    private float hinge = Float.NaN;
    private float hall = Float.NaN;
    private boolean sensorsAvailable;

    public void setSensorsAvailable(boolean value) { sensorsAvailable = value; }
    public void setHinge(float value) {
        hinge = Float.isFinite(value) && value >= 0 && value <= 360 ? value : Float.NaN;
    }
    public void setHall(float value) {
        hall = value == 0 || value == 1 ? value : Float.NaN;
    }
    public float getHinge() { return hinge; }
    public float getHall() { return hall; }
    public boolean hasSensors() { return sensorsAvailable; }

    public int evaluate(int current) {
        if (!sensorsAvailable || !Float.isFinite(hinge) || !Float.isFinite(hall)) return OPEN;
        // Reopening follows the wakeup hinge sensor even if the on-change Hall update is late.
        if (current == CLOSED) return hinge >= 10 ? OPEN : CLOSED;
        // Two captured closes reached Hall0=0 at approximately zero degrees.
        // Fold-back reached ~341 degrees with Hall0=1 and must never imply sleep.
        return hall == 0 && hinge <= 3 ? CLOSED : OPEN;
    }
}
