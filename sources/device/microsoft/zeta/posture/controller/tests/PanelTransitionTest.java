// SPDX-License-Identifier: Apache-2.0
package org.lineageos.zeta.posturecontroller;
import java.util.ArrayList;
import java.util.List;
public final class PanelTransitionTest {
    private static final class Ports implements PanelTransition.Ports {
        final List<String> calls=new ArrayList<>();String fail,recoveryFail;boolean stale;int before=2;
        void call(String name)throws Exception{calls.add(name);if(name.equals(fail) || name.equals(recoveryFail))throw new Exception(name);}
        public void viewport(int mode)throws Exception{call("viewport"+mode);}
        public int current()throws Exception{call("read");return before;}
        public void display(int mode)throws Exception{call("display"+mode);}
        public void touch(int mode)throws Exception{call("touch"+mode);}
        public void interactive(boolean reset)throws Exception{call("interactive"+reset);}
        public boolean stillCurrent(){return !stale;}
        public void restoreViewport(boolean pause)throws Exception{call("restoreViewport"+pause);}
    }
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception{
        Ports good=new Ports();PanelTransition.apply(good,1);
        check(good.calls.equals(List.of("read","viewport1","display1","touch1","interactivefalse")),"Successful order");
        Ports left=new Ports();left.before=0;PanelTransition.apply(left,2);
        check(left.calls.contains("interactivetrue"),"LEFT exit must reset touch");
        for(String stage:List.of("read","viewport1","display1","touch1","interactivefalse")){
            Ports broken=new Ports();broken.fail=stage;
            try{PanelTransition.apply(broken,1);throw new AssertionError("Expected failure at "+stage);}catch(Exception expected){}
            check(broken.calls.contains("restoreViewporttrue"),"Failure must pause and restore viewport: "+stage);
            check(broken.calls.contains("display2") && broken.calls.contains("touch2"),"Independent HAL rollback: "+stage);
        }
        for(String recovery:List.of("restoreViewporttrue","display2","touch2","interactivefalse")){
            Ports broken=new Ports();broken.fail="viewport1";broken.recoveryFail=recovery;
            try{PanelTransition.apply(broken,1);throw new AssertionError("Expected rollback failure");}catch(Exception expected){}
            check(broken.calls.containsAll(List.of("restoreViewporttrue","display2","touch2","interactivefalse")),"One rollback failure must not prevent other legs: "+recovery);
        }
        Ports cancelled=new Ports();cancelled.stale=true;
        try{PanelTransition.apply(cancelled,1);throw new AssertionError("Expected cancellation");}catch(PanelTransition.Cancelled expected){}
        check(cancelled.calls.contains("restoreViewportfalse") && !cancelled.calls.contains("restoreViewporttrue"),"Rapid posture change must not permanently pause");
        check(!cancelled.calls.contains("display1"),"Stale request must not select the old panel");
        Ports staleAndBroken=new Ports();staleAndBroken.stale=true;staleAndBroken.recoveryFail="display2";
        try{PanelTransition.apply(staleAndBroken,1);throw new AssertionError("Expected cancellation");}
        catch(PanelTransition.Cancelled expected){check(expected.getSuppressed().length>0,"Failed cancellation recovery must be observable to the controller");}
        Ports invalid=new Ports();try{PanelTransition.apply(invalid,3);throw new AssertionError("Invalid mode");}catch(IllegalArgumentException expected){}
        check(invalid.calls.isEmpty(),"Never send NONE/SPLIT or invalid mode");
        System.out.println("PASS transition ordering, LEFT reset, every failure leg, stale cancellation and invalid-mode guard");
    }
}
