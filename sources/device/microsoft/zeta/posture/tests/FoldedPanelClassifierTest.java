// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

public final class FoldedPanelClassifierTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        check(FoldedPanelClassifier.evaluate(Float.NaN,7,1)==2,"Unknown hinge must retain both");
        check(FoldedPanelClassifier.evaluate(336,99,1)==2,"Unknown posture must retain both");
        check(FoldedPanelClassifier.evaluate(180,7,1)==2,"Stale single posture cannot hide a panel when flat");
        check(FoldedPanelClassifier.evaluate(0,7,1)==2,"Closed power state must not select a single panel");
        check(FoldedPanelClassifier.evaluate(299,7,2)==2,"Entry threshold");
        check(FoldedPanelClassifier.evaluate(300,7,2)==1,"Observed right posture");
        check(FoldedPanelClassifier.evaluate(280,7,1)==1,"Exit hysteresis");
        check(FoldedPanelClassifier.evaluate(260,7,1)==2,"Reliable return to both");
        check(FoldedPanelClassifier.evaluate(336,13,2)==0,"Reference left-side planning case (not physically verified)");
        Pattern pattern=Pattern.compile("EVENT elapsedMs=(\\d+) type=(\\d+) values=\\[([^]]+)\\]");
        int composition=2,posture=-1,singleEntries=0,returns=0;float hinge=Float.NaN;
        for(String line:Files.readAllLines(Path.of(args[0]))) {
            Matcher match=pattern.matcher(line);if(!match.find())continue;
            int type=Integer.parseInt(match.group(2));float value=Float.parseFloat(match.group(3).split(",")[0]);
            if(type==36)hinge=value;else if(type==33171009)posture=(int)value;else continue;
            int next=FoldedPanelClassifier.evaluate(hinge,posture,composition);
            if(next!=composition) {
                if(next==1)singleEntries++;if(next==2)returns++;
                composition=next;
            }
            if(hinge<=260)check(composition==2,"Trace returned toward flat but model hid a panel");
        }
        check(singleEntries>=1 && returns>=1 && composition==2,"Measured trace must enter right then return both");
        System.out.println("PASS folded-panel planning: measured right entries="+singleEntries+", returns-to-both="+returns+"; left mapping still requires device test");
    }
}
