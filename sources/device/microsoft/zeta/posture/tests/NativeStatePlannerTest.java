// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.devicestate;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
public final class NativeStatePlannerTest{
    private static void check(boolean b,String why){if(!b)throw new AssertionError(why);}
    public static void main(String[] args)throws Exception{
        PostureClassifier core=new PostureClassifier();core.setSensorsAvailable(true);core.setHall(0);core.setHinge(0);
        check(NativeStatePlanner.desired(false,false,core,0,1)==1,"No sleep before boot complete");
        check(NativeStatePlanner.desired(true,true,core,0,1)==0,"Manual both mode must retain physical-close sleep");
        core.setHall(1);core.setHinge(335);
        check(NativeStatePlanner.desired(true,true,core,7,2)==1,"Pause blocks single mode");
        check(NativeStatePlanner.desired(true,false,core,-1,1)==1,"Missing private posture retains both");
        check(NativeStatePlanner.desired(true,false,core,7,1)==2,"Measured right posture");
        core.setSensorsAvailable(false);
        check(NativeStatePlanner.desired(true,false,core,7,2)==1,"Missing wakeup sensors retain both");
        core=new PostureClassifier();core.setSensorsAvailable(true);
        int state=1,pending=-1,posture=-1,closes=0,right=0,left=0;long deadline=-1;
        Pattern pattern=Pattern.compile("EVENT elapsedMs=(\\d+) type=(\\d+) values=\\[([^]]+)\\]");
        for(String line:Files.readAllLines(Path.of(args[0]))){
            Matcher m=pattern.matcher(line);if(!m.find())continue;
            long now=Long.parseLong(m.group(1));int type=Integer.parseInt(m.group(2));float value=Float.parseFloat(m.group(3).split(",")[0]);
            if(deadline>=0 && now>=deadline && NativeStatePlanner.desired(true,false,core,posture,state)==pending){
                state=pending;if(state==0)closes++;if(state==2)right++;if(state==3)left++;deadline=-1;pending=-1;
            }
            if(type==36){core.setHinge(value);if(value<=260)posture=-1;}
            else if(type==33171002)core.setHall(value);
            else if(type==33171009)posture=(int)value;
            else continue;
            int next=NativeStatePlanner.desired(true,false,core,posture,state);
            if(next==1){state=1;deadline=-1;pending=-1;}
            else if(next!=state && pending!=next){pending=next;deadline=now+(next==0?100:150);}
        }
        check(closes==2 && right==1 && left==0 && state==1,"Captured native state sequence: closed="+closes+" right="+right+" left="+left+" final="+state);
        System.out.println("PASS native state startup/pause/failure checks; measured trace:2 closes,1 right fold, final dual");
    }
}
