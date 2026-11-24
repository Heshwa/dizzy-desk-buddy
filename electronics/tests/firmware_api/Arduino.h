#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
#include <cctype>
#include <algorithm>
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
inline uint32_t fakeNow=1000;inline int gpio[64]={};
inline uint32_t millis(){return fakeNow;}inline void delay(uint32_t n){fakeNow+=n;}
inline void pinMode(int,int){}inline void digitalWrite(int pin,int v){gpio[pin]=v;}inline int digitalRead(int pin){return gpio[pin];}
template<class T>T constrain(T n,T lo,T hi){return std::min(std::max(n,lo),hi);}
class String:public std::string{public:using std::string::string;using std::string::operator=;void trim(){auto p=find_first_not_of(" \r\n\t");if(p==npos){clear();return;}erase(0,p);erase(find_last_not_of(" \r\n\t")+1);}void toLowerCase(){for(auto &c:*this)c=std::tolower((unsigned char)c);}};
struct SerialMock{std::string output;void begin(int){}void setTimeout(int){}void println(const char*s){output+=s;output+='\n';}template<class...Args>void printf(const char*f,Args...args){char b[512];std::snprintf(b,sizeof b,f,args...);output+=b;}int available(){return 0;}int read(){return -1;}};
inline SerialMock Serial;
