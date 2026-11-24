// Dizzy electronics bring-up demo. No network secrets and no production audio firmware.
// Digital buttons stand in for the two capacitive electrodes in this simulation.
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <string.h>
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include "pins.h"
#include "face_assets.h"
#define DIZZY_SIMULATION 1
// Software SPI exposes the complete byte stream to Wokwi's custom LCD.
// Draw only changed features; no full-frame allocation on the ESP32.
Adafruit_GC9A01A lcd(LCD_CS,LCD_DC,LCD_MOSI,LCD_SCK,LCD_RESET);
bool powerOK=false, listening=false, ringing=false, quiet=false;
int volume=50, angle[3]={90,0,0}, target[3]={90,0,0};
uint32_t nextPower=0,nextMotion=0,nextFace=0,nextStatus=0,alarmAt=0,happyUntil=0,waveStart=0,cameraUntil=0;
FaceMode previewFace=FACE_IDLE;uint32_t previewUntil=0;
uint32_t lastActivity=0,strokeAt=0;int strokeZone=-1;bool stroked[2]={false,false};
uint32_t petDown[2]={0,0},lastTap=0;int waveMode=0;bool pendingTap=false;
struct Key {int pin;bool raw,stable;uint32_t changed;};
Key keys[]={{TALK_BUTTON,1,1,0},{VOLUME_DOWN,1,1,0},{VOLUME_UP,1,1,0},{PET_LEFT,1,1,0},{PET_RIGHT,1,1,0}};
bool writeReg(uint8_t address,uint8_t reg,uint8_t value) {
 Wire.beginTransmission(address);Wire.write(reg);Wire.write(value);return Wire.endTransmission()==0;
}
int readReg(uint8_t address,uint8_t reg) {
 Wire.beginTransmission(address);Wire.write(reg);if(Wire.endTransmission(false))return -1;
 if(Wire.requestFrom(address,(uint8_t)1)!=1)return -1;return Wire.read();
}
void servoWrite(int channel,int degrees) {
 uint16_t us=500+(uint32_t)constrain(degrees,0,180)*2000/180;
 uint16_t ticks=(uint32_t)us*4096/20000;
 Wire.beginTransmission(0x40);Wire.write(6+4*channel);
 Wire.write(0);Wire.write(0);Wire.write(ticks&255);Wire.write(ticks>>8);Wire.endTransmission();
}
void powerCheck() {
 int status=readReg(0x08,0),detail=readReg(0x08,1);
 bool safe=status>=0 && detail>=0 && (status>>4)==1 && (status&15)==15 && (detail&64) && ((detail>>3)&7)==1;
 safe=safe && readReg(0x40,0)>=0 && readReg(0x68,0)>=0;
 if(safe!=powerOK)Serial.println(safe?"POWER_OK: model reports 5V/5A; OE enabled":"POWER_BLOCKED: outputs disabled (OE HIGH)");
 powerOK=safe;digitalWrite(SERVO_OUTPUTS_ENABLE,powerOK?LOW:HIGH);
}
#include "face_renderer.h"
void pose(int mode) { if(quiet || ringing)return;waveStart=millis();waveMode=mode; }
void tap() {
 if(ringing){ringing=false;alarmAt=millis()+5*60*1000UL;Serial.println("ALARM_SNOOZED: 5 minutes");return;}
 if(pendingTap && millis()-lastTap<350){pendingTap=false;pose(1);Serial.println("DOUBLE_TAP: local wave; MQTT delivery not emulated here");}
 else {pendingTap=true;lastTap=millis();}
}
void pressed(int id) {
 lastActivity=millis();
 if(id==0){listening=!listening;Serial.println(listening?"PTT_START: microphone/LLM uses the Mac service":"PTT_STOP");}
 else if(id==1||id==2){volume=constrain(volume+(id==2?5:-5),0,100);Serial.printf("VOLUME=%d (audio path wiring only)\n",volume);}
 else {
  int zone=id-3;petDown[zone]=millis();stroked[zone]=false;previewUntil=0;
  if(strokeZone>=0 && strokeZone!=zone && millis()-strokeAt<800){
   pendingTap=false;stroked[0]=stroked[1]=true;strokeZone=-1;
   happyUntil=millis()+3000;pose(3);Serial.println("PET_STROKE: happy + both hands (chirp in Webots only)");
  }else{strokeZone=zone;strokeAt=millis();}
 }
}
void released(int id) {
 if(id<3)return;
 uint32_t held=millis()-petDown[id-3];petDown[id-3]=0;
 if(ringing){tap();return;}
 if(stroked[id-3]){stroked[id-3]=false;return;}
 if(held>=1200){pendingTap=false;happyUntil=0;previewFace=FACE_GOODNIGHT;previewUntil=millis()+6000;pose(4);Serial.println("GOODNIGHT: network delivery remains in Webots/Mac");}
 else tap();
}
void command(String text) {
 text.trim();text.toLowerCase();lastActivity=millis();
 for(int i=0;i<FACE_COUNT;i++){String request="face ";request+=FACE_NAMES[i];if(text==request){listening=false;happyUntil=0;previewFace=(FaceMode)i;previewUntil=millis()+8000;Serial.printf("FACE_PREVIEW=%s (visual only)\n",FACE_NAMES[i]);return;}}
 if(text=="left")target[0]=45;else if(text=="right")target[0]=135;else if(text=="center")target[0]=90;
 else if(text=="wave"||text=="hello"){pose(text=="hello"?2:1);}
 else if(text=="alarm"){alarmAt=millis()+5000;Serial.println("ALARM_TEST: five seconds");}
 else if(text=="dismiss"){ringing=false;alarmAt=0;}
 else if(text=="quiet"){quiet=!quiet;Serial.printf("QUIET=%d\n",quiet);}
 else if(text=="photo"){cameraUntil=millis()+1000;Serial.println("CAMERA_LED_TEST only: no image captured in circuit simulator");}
 else if(text.length())Serial.println("Commands: left right center wave hello alarm dismiss quiet photo; face idle/happy/sleepy/listening/thinking/speaking/alarm/heart/goodnight/music/blink");
}
void setup() {
 Serial.begin(115200);Serial.setTimeout(10);
 digitalWrite(SERVO_OUTPUTS_ENABLE,HIGH);pinMode(SERVO_OUTPUTS_ENABLE,OUTPUT);pinMode(CAMERA_ACTIVITY_LED,OUTPUT);
 for(auto &key:keys)pinMode(key.pin,INPUT); // External pull-ups on all simulation inputs.
 Wire.begin(RTC_SDA,RTC_SCL);Wire.setClock(100000);
 Serial.println("DIZZY ELECTRONICS DEMO: digital/register models, not electrical qualification");
 for(int address: {0x08,0x40,0x68}){Wire.beginTransmission(address);Serial.printf("I2C 0x%02X %s\n",address,Wire.endTransmission()==0?"ACK":"MISSING");}
 writeReg(0x40,0,0x30);writeReg(0x40,254,121);writeReg(0x40,0,0x20);
 for(int i=0;i<3;i++)servoWrite(i,angle[i]);
 writeReg(0x08,8,0x10);writeReg(0x08,9,1); // Only request the 5V source PDO.
 lcd.begin();lcd.setRotation(0);
 delay(50);powerCheck();drawFace();Serial.println("READY: click the five buttons; use Serial commands for motor/alarm tests");
}
void loop() {
 uint32_t now=millis();
 for(int i=0;i<5;i++) {
  bool value=digitalRead(keys[i].pin);
  if(value!=keys[i].raw){keys[i].raw=value;keys[i].changed=now;}
  if(now-keys[i].changed>=25 && value!=keys[i].stable){keys[i].stable=value;if(!value)pressed(i);else released(i);}
 }
 if(pendingTap && now-lastTap>350){pendingTap=false;happyUntil=now+2000;pose(3);Serial.println("PET_TAP: happy blink (local)");}
 if(now>=nextPower){nextPower=now+500;powerCheck();}
 if(ringing){waveMode=0;target[1]=target[2]=0;}
 if(waveMode){uint32_t phase=now-waveStart;int left=0,right=0;uint32_t end=0;
  if(waveMode==1){right=phase<2200?118:phase<3100?75:phase<4000?118:phase<4900?75:phase<5800?118:0;end=5800;}
  if(waveMode==2){left=right=phase<2200?118:phase<3100?80:phase<4200?118:0;end=4200;}
  if(waveMode==3){left=right=phase<1200?40:0;end=1200;}
  if(waveMode==4){left=right=phase<1000?20:0;end=1000;}
  target[1]=left;target[2]=right;if(phase>=end)waveMode=0;
 }
 if(now>=nextMotion){nextMotion=now+20;if(powerOK)for(int i=0;i<3;i++){
  int delta=constrain(target[i]-angle[i],-2,2);if(delta){angle[i]+=delta;servoWrite(i,angle[i]);}
 }}
 if(alarmAt && (int32_t)(now-alarmAt)>=0){alarmAt=0;ringing=true;Serial.println("ALARM_RINGING: visual only; touch snoozes");}
 digitalWrite(CAMERA_ACTIVITY_LED,now<cameraUntil?HIGH:LOW);
 if(now>=nextFace){nextFace=now+80;drawFace();}
 if(now>=nextStatus){nextStatus=now+2000;Serial.printf("STATUS power=%d OE=%d neck=%d left=%d right=%d volume=%d alarm=%d\n",powerOK,!powerOK,angle[0]-90,angle[1],angle[2],volume,ringing);}
 static String line;while(Serial.available()){char c=Serial.read();if(c=='\n'){command(line);line="";}else if(c!='\r' && line.length()<64)line+=c;}
 delay(1);
}
