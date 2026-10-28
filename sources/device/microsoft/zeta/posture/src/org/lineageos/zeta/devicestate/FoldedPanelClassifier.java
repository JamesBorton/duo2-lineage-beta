// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;

/** Pure planning model; it never calls HAL, window, touch or power APIs. */
public final class FoldedPanelClassifier {
    public static final int LEFT = 0;
    public static final int RIGHT = 1;
    public static final int BOTH = 2;
    public static int evaluate(float hinge, int posture, int current) {
        if (!Float.isFinite(hinge) || hinge < 0 || hinge > 360) return BOTH;
        // Captured right-side fold reached ~336 degrees. Keep a wide return margin.
        boolean alreadySingle = current == LEFT || current == RIGHT;
        if (hinge <= 260 || (!alreadySingle && hinge < 300)) return BOTH;
        switch (posture) {
            // Functional enum meanings from the pinned reference interface consumer.
            // Right code7 was observed; left-side cases still need physical confirmation.
            case 7: case 8: case 9: case 10: case 15: return RIGHT;
            case 11: case 12: case 13: case 14: case 16: return LEFT;
            default: return BOTH;
        }
    }
    private FoldedPanelClassifier() { }
}
