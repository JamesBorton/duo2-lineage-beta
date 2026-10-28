// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Boundary/failure cases plus replay of the actual phone movement capture. */
public final class PostureClassifierTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        PostureClassifier c = new PostureClassifier();
        check(c.evaluate(0) == 1, "Unavailable sensors must leave OPEN");
        c.setSensorsAvailable(true);
        c.setHall(0);
        check(c.evaluate(1) == 1, "Missing hinge must not close");
        c.setHinge(3);
        check(c.evaluate(1) == 0, "Measured Hall close plus low angle");
        c.setHinge(9);
        check(c.evaluate(0) == 0, "Closed state hysteresis");
        c.setHinge(10);
        check(c.evaluate(0) == 1, "Reopen despite a delayed Hall update");
        c.setHinge(341);
        check(c.evaluate(1) == 1, "Fold-back cannot trigger sleep, even with stale Hall=0");
        c.setHinge(Float.NaN);
        check(c.evaluate(0) == 1, "Invalid angle leaves OPEN");
        c.setHinge(0);
        c.setHall(2);
        check(c.evaluate(1) == 1, "Unrecognized Hall value cannot close");
        c.setHall(0);
        c.setSensorsAvailable(false);
        check(c.evaluate(0) == 1, "Lost registration leaves OPEN");

        c = new PostureClassifier();
        c.setSensorsAvailable(true);
        int state = 1, closes = 0, opens = 0, samples = 0;
        long pendingClose = -1;
        Pattern pattern = Pattern.compile("elapsedMs=(\\d+) sensor=.*? type=(\\d+) wake=true values=\\[([^],]+)");
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            Matcher m = pattern.matcher(line);
            if (!m.find()) continue;
            long now = Long.parseLong(m.group(1));
            int type = Integer.parseInt(m.group(2));
            if (type != 36 && type != 33171002) continue;
            if (pendingClose >= 0 && now >= pendingClose && c.evaluate(state) == 0) {
                state = 0; closes++; pendingClose = -1;
            }
            float value = Float.parseFloat(m.group(3));
            if (type == 36) c.setHinge(value); else c.setHall(value);
            samples++;
            int desired = c.evaluate(state);
            if (desired == 0 && state == 1) {
                if (pendingClose < 0) pendingClose = now + 100;
            } else {
                pendingClose = -1;
                if (desired != state) { state = desired; if (state == 1) opens++; }
            }
            if (type == 36 && value >= 300) check(state == 1, "Measured fold-back must remain awake");
        }
        check(samples > 100, "Expected actual sensor trace");
        check(closes == 2 && opens == 2 && state == 1, "Capture must replay two close/reopen cycles: " + closes + "/" + opens);
        System.out.println("PASS boundaries/fail-open; measured wakeup samples=" + samples + ", closes=" + closes + ", reopens=" + opens);
    }
}
