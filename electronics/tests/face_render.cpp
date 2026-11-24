#include <fstream>
#include <string>
#include <iostream>
#include "../wokwi/sketch.ino"
void save(const std::string &file){std::ofstream out(file,std::ios::binary);out<<"P6\n240 240\n255\n";for(auto p:lcd.pixels){char rgb[3]={(char)(((p>>11)&31)*255/31),(char)(((p>>5)&63)*255/63),(char)((p&31)*255/31)};out.write(rgb,3);}}
int main(int argc,char **argv){
 Wire.regs[8][0]=0x1f;Wire.regs[8][1]=0x48;Wire.regs[0x68][2]=0x13;Wire.regs[0x68][1]=0x20;powerCheck();
 for(int mode=0;mode<FACE_COUNT;mode++) {
  int count=FACE_GROUPS[mode].count;
  for(int phase=0;phase<count;phase++) {
   fakeNow=count==1?1000:(mode==FACE_MUSIC?63:90)*(16+phase);
   String request="face ";request+=FACE_NAMES[mode];command(request);drawFace();
   save(std::string(argv[1])+"/"+FACE_NAMES[mode]+"-"+std::to_string(phase)+".ppm");
  }
 }
}
