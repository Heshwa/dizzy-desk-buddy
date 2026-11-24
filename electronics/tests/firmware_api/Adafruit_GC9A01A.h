#pragma once
#include <cstdint>
class Adafruit_GC9A01A{public:
 uint16_t pixels[240*240]={};
 Adafruit_GC9A01A(int,int,int,int,int){}void begin(){}void setRotation(int){}
 void drawFastHLine(int x,int y,int width,uint16_t color){if(y<0||y>=240)return;for(int i=x;i<x+width;i++)if(i>=0&&i<240)pixels[y*240+i]=color;}
 void fillRoundRect(int,int,int,int,int,uint16_t){}void setTextSize(int){}void setCursor(int,int){}void setTextColor(uint16_t){}template<class T>void print(T){}
};
