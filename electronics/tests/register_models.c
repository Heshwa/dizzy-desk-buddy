#include "wokwi-api.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int values[64],np,nt;static char names[64][32];static uint32_t delays[16],amps=5;
static uint64_t nanos;static i2c_config_t bus;
pin_t pin_init(const char*n,int m){for(int i=1;i<=np;i++)if(!strcmp(names[i],n))return i;int p=++np;snprintf(names[p],32,"%s",n);values[p]=m==INPUT_PULLUP||m==OUTPUT_HIGH;return p;}
uint32_t pin_read(pin_t p){return values[p];}void pin_write(pin_t p,uint32_t v){values[p]=v;}
timer_t timer_init(const timer_config_t*c){return ++nt;}void timer_start(timer_t t,uint32_t us,bool repeat){delays[t]=us;}
void pin_watch(pin_t p,const pin_watch_config_t*w){}void i2c_init(const i2c_config_t*c){bus=*c;}
uint32_t attr_init(const char*n,uint32_t v){return 1;}uint32_t attr_read(uint32_t a){return amps;}uint64_t get_sim_nanos(void){return nanos;}
#include "../wokwi/dizzy_devices.h"
static void regwrite(peripheral*p,int r,int v){connect_bus(p,CHIP_ADDRESS,false);write_bus(p,r);write_bus(p,v);}
static int regread(peripheral*p,int r){connect_bus(p,CHIP_ADDRESS,false);write_bus(p,r);connect_bus(p,CHIP_ADDRESS,true);return read_bus(p);}
int main(void){
 chip_init();peripheral*p=bus.user_data;values[p->ground]=0;values[p->vcc]=1;
 assert(bus.address==CHIP_ADDRESS);assert(connect_bus(p,CHIP_ADDRESS,false));
 values[p->vcc]=0;assert(!connect_bus(p,CHIP_ADDRESS,false));values[p->vcc]=1;
#if CHIP_KIND==1
 assert(regread(p,2)==0x13);assert(regread(p,1)==0x20);nanos=65000000000ULL;
 assert(regread(p,0)==0x05);assert(regread(p,1)==0x21);puts("PASS RTC BCD reads, time advance and missing-power NACK");
#elif CHIP_KIND==2
 values[p->supply]=1;values[p->oe]=0;regwrite(p,0,0x20);regwrite(p,254,121);
 regwrite(p,6,0);regwrite(p,7,0);regwrite(p,8,307&255);regwrite(p,9,307>>8);
 pulse(&p->channels[0]);assert(values[p->pwm[0]]==1);assert(delays[p->channels[0].timer]>=1490&&delays[p->channels[0].timer]<=1510);
 pulse(&p->channels[0]);assert(values[p->pwm[0]]==0);assert(delays[p->channels[0].timer]>18000);
 pulse(&p->channels[0]);values[p->oe]=1;output_disable(p,p->oe,1);assert(values[p->pwm[0]]==0);pulse(&p->channels[0]);assert(values[p->pwm[0]]==0);
 values[p->oe]=0;values[p->supply]=0;pulse(&p->channels[0]);assert(!values[p->pwm[0]]);
 values[p->supply]=1;regwrite(p,0,0x30);pulse(&p->channels[0]);assert(!values[p->pwm[0]]);
 puts("PASS PCA 50Hz pulse, center width, OE inhibit, missing V+ and sleep inhibit");
#else
 assert(regread(p,0)==0);regwrite(p,8,0x10);regwrite(p,9,1);assert(regread(p,0)==0x1f);assert(regread(p,1)==0x48);
 amps=4;assert(regread(p,0)==0x1d);amps=3;assert(regread(p,0)==0x1a);amps=1;assert(regread(p,0)==0x12);
 regwrite(p,8,0x20);regwrite(p,9,1);assert(regread(p,0)==0);
 puts("PASS PD 5V contract register, 5A/3A/1A fault settings, reject other voltage request");
#endif
}
