#include <Wire.h>
#include <math.h>

constexpr int PCA=0x40,IO=0x20,ADC=0x48,RTC=0x68,IMU=0x69,OE=16;
bool armed=false,voice=false,fault=false;
uint8_t last=0;
uint32_t start=0,capture=0;

bool writeReg(int address,int reg,uint8_t value){
  Wire.beginTransmission(address);Wire.write(reg);Wire.write(value);
  return Wire.endTransmission()==0;
}
bool readReg(int address,int reg,uint8_t *out,int count){
  Wire.beginTransmission(address);Wire.write(reg);
  if(Wire.endTransmission(false)!=0 || Wire.requestFrom(address,count)!=count)return false;
  for(int i=0;i<count;++i)out[i]=Wire.read();
  return true;
}
void pose(){
  double phase=(millis()-start)*.005;
  uint8_t frame[32]={};
  for(int i=0;i<8;++i){
    int extent=i<2?12:i<4?24:15;
    int count=(int)((1500+(armed?9.2*extent*sin(phase+i*.7):0))*4096/20000);
    frame[4*i+2]=count&255;frame[4*i+3]=(count>>8)&15;
  }
  Wire.beginTransmission(PCA);Wire.write(6);Wire.write(frame,sizeof frame);
  digitalWrite(OE,(Wire.endTransmission()==0 && armed && !fault)?LOW:HIGH);
}
void setup(){
  pinMode(OE,OUTPUT_OPEN_DRAIN);digitalWrite(OE,HIGH);
  Serial.begin(115200);Wire.begin(17,18,100000);
  writeReg(PCA,0,0x30);writeReg(PCA,254,121);writeReg(PCA,1,4);writeReg(PCA,0,0x20);
  writeReg(IO,0,255);writeReg(IO,0x0c,255);
  uint8_t id=0,time[3]={};
  bool imu=readReg(IMU,0,&id,1)&&id==0x24,rtc=readReg(RTC,0,time,3);
  Serial.printf("DIZZY V2 HARNESS | BMI fixture %s | RTC %02x:%02x:%02x | %s\n",
    imu?"OK":"FAIL",time[2],time[1],time[0],rtc?"OK":"FAIL");
}
void loop(){
  uint8_t input=255, v[2]={}, gravity[6]={};
  bool safe=readReg(IO,0x12,&input,1) && readReg(ADC,0,v,2) && readReg(IMU,0xc,gravity,6);
  uint8_t down=(uint8_t)~input, rising=down&~last;last=down;
  float volts=((v[0]<<8)|v[1])*.0005f;
  bool tilt=gravity[5]<0x30;
  bool cut=(down&16)||!safe||volts<6.8||tilt;
  if(cut&&armed){fault=true;armed=false;Serial.println("MOTOR LOCKOUT");}
  if((rising&8)&&!cut){armed=!armed;fault=false;start=millis();Serial.printf("ARMED %d\n",armed);}
  if(rising&1){voice=!voice;capture=millis();Serial.println(voice?"RECORDING fixture":"STOP fixture");}
  if(voice&&millis()-capture>=30000){voice=false;Serial.println("STOP after 30 seconds");}
  if(rising&2)Serial.println("PET left");
  if(rising&4)Serial.println("PET right");
  pose();
  delay(35);
}
