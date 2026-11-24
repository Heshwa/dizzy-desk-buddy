#pragma once
#include <cstdint>
struct WireMock {int address=0,pointer=0,n=0;int regs[128][256]={};bool missing[128]={};
 void begin(int,int){}void setClock(int){}void beginTransmission(uint8_t a){address=a;n=0;}
 void write(int v){if(n++==0)pointer=v;else regs[address][pointer++&255]=v;}
 int endTransmission(bool=true){return missing[address]?4:0;}int requestFrom(uint8_t a,uint8_t count){address=a;return missing[a]?0:count;}
 int read(){return regs[address][pointer&255];}};
inline WireMock Wire;
