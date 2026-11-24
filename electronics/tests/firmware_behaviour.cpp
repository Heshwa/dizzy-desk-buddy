// Executes the actual sketch's action/state functions with deterministic time.
// Does not emulate ESP32 hardware, LCD graphics, audio or physical button bounce.
#include <cassert>
#include <iostream>
#include "../wokwi/sketch.ino"
int main(){
 for(int i=0;i<64;i++)gpio[i]=HIGH;
 Wire.regs[8][0]=0x1f;Wire.regs[8][1]=0x48;powerCheck();assert(powerOK&&gpio[16]==LOW);
 Wire.regs[8][0]=0x1a;powerCheck();assert(!powerOK&&gpio[16]==HIGH);
 Wire.regs[8][0]=0x1f;Wire.missing[0x40]=true;powerCheck();assert(!powerOK&&gpio[16]==HIGH);
 Wire.missing[0x40]=false;powerCheck();assert(powerOK);
 fakeNow=2000;tap();assert(pendingTap);fakeNow=2400;loop();assert(!pendingTap);assert(Serial.output.find("PET_TAP")!=std::string::npos);assert(waveMode==3&&selectedFace(fakeNow)==FACE_HAPPY);
 fakeNow=3000;tap();fakeNow=3200;tap();assert(!pendingTap&&waveMode==1);assert(Serial.output.find("DOUBLE_TAP")!=std::string::npos);
 waveMode=0;target[1]=target[2]=118;fakeNow=4000;pressed(3);fakeNow=5300;released(3);assert(waveMode==4);assert(Serial.output.find("GOODNIGHT")!=std::string::npos);
 // Compare local reactions with Webots' documented arm/expression sequence.
 fakeNow=5500;pressed(3);fakeNow=5600;pressed(4);released(3);released(4);
 assert(waveMode==3&&!pendingTap&&selectedFace(fakeNow)==FACE_HAPPY);
 fakeNow=5700;loop();assert(target[1]==40&&target[2]==40);
 fakeNow=6900;loop();assert(target[1]==0&&target[2]==0);
 previewUntil=happyUntil=0;lastActivity=7000;quiet=true;fakeNow=7100;assert(selectedFace(fakeNow)==FACE_IDLE);
 fakeNow=37000;assert(selectedFace(fakeNow)==FACE_SLEEPY);quiet=false;
 fakeNow=38000;pose(1);loop();assert(target[2]==118&&target[1]==0);
 fakeNow=42100;loop();assert(target[2]==75); // Webots wave's fourth stage.
 ringing=true;loop();assert(!waveMode&&target[1]==0&&target[2]==0&&selectedFace(fakeNow)==FACE_ALARM);
 ringing=true;fakeNow=43000;tap();assert(!ringing&&alarmAt==343000);
 command(String("right"));for(int i=0;i<100;i++){fakeNow+=20;loop();assert(angle[0]>=45&&angle[0]<=135);}assert(angle[0]==135);
 command(String("left"));for(int i=0;i<100;i++){fakeNow+=20;loop();assert(angle[0]>=45&&angle[0]<=135);}assert(angle[0]==45);
 Wire.regs[8][0]=0x1a;powerCheck();command(String("right"));int saved=angle[0];for(int i=0;i<20;i++){fakeNow+=20;loop();}assert(angle[0]==saved&&gpio[16]==HIGH);
 for(int i=0;i<30;i++)pressed(1);assert(volume==0);for(int i=0;i<30;i++)pressed(2);assert(volume==100);
 std::cout<<"PASS actual sketch: power interlock, missing-device inhibit, pet/double/hold gestures, snooze, neck limits, blocked motion and volume clamps\n";
}
