// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;
/** Pure combined state decision; scheduling and IPC remain outside the model. */
final class NativeStatePlanner {
    static int desired(boolean booted,boolean paused,PostureClassifier core,int posture,int current){
        if(!booted || !core.hasSensors())return 1;
        if(core.evaluate(current)==0)return 0;
        if(paused)return 1;
        int composition=current==2?FoldedPanelClassifier.RIGHT:current==3?FoldedPanelClassifier.LEFT:FoldedPanelClassifier.BOTH;
        int next=FoldedPanelClassifier.evaluate(core.getHinge(),posture,composition);
        return next==FoldedPanelClassifier.RIGHT?2:next==FoldedPanelClassifier.LEFT?3:1;
    }
    private NativeStatePlanner(){}
}
