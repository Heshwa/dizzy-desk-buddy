// Functional register models only: not transistor-level or vendor-certified models.
#include "wokwi-api.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct peripheral peripheral;
typedef struct { peripheral *dev; int channel; timer_t timer; bool high; } pwm_channel;
struct peripheral {
  uint8_t regs[256], pointer; bool first; pin_t vcc, ground, oe, supply, pwm[3];
  uint32_t current_attr; bool pd_requested; pwm_channel channels[3];
};
static uint8_t bcd(unsigned n) { return ((n/10)<<4)|(n%10); }
static bool powered(peripheral *p) { return pin_read(p->vcc) && !pin_read(p->ground); }
static void pulse(void *data) {
  pwm_channel *c=data; peripheral *p=c->dev;
  bool enabled=powered(p) && pin_read(p->supply) && !pin_read(p->oe) && !(p->regs[0]&0x10);
  unsigned offset=6+c->channel*4;
  unsigned on=p->regs[offset]|((p->regs[offset+1]&15)<<8);
  unsigned off=p->regs[offset+2]|((p->regs[offset+3]&15)<<8);
  unsigned counts=(off-on)&4095;
  unsigned period=(unsigned)((p->regs[254]+1)*4096.0/25.0);
  if(period<1000)period=20000;
  unsigned width=(unsigned)(counts*(period/4096.0));
  if(!enabled || (p->regs[offset+3]&16) || !counts) {
    pin_write(p->pwm[c->channel],LOW);c->high=false;timer_start(c->timer,1000,false);return;
  }
  c->high=!c->high;pin_write(p->pwm[c->channel],c->high?HIGH:LOW);
  timer_start(c->timer,c->high?(width?width:1):(period>width?period-width:1),false);
}
static void output_disable(void *data,pin_t pin,uint32_t value) {
  peripheral *p=data;
  if(value)for(int i=0;i<3;i++){pin_write(p->pwm[i],LOW);p->channels[i].high=false;}
}
static bool connect_bus(void *data,uint32_t address,bool read) {
  peripheral *p=data;if(!read)p->first=true;return powered(p);
}
static bool write_bus(void *data,uint8_t value) {
  peripheral *p=data;
  if(p->first){p->pointer=value;p->first=false;return true;}
  uint8_t reg=p->pointer;
  p->regs[reg]=value;
#if CHIP_KIND == 3
  if(reg==9 && (value&1))p->pd_requested=(p->regs[8]>>4)==1;
#endif
#if CHIP_KIND == 2
  if(p->regs[0]&32)p->pointer++;
#else
  p->pointer++;
#endif
  return true;
}
static uint8_t read_bus(void *data) {
  peripheral *p=data;uint8_t reg=p->pointer++;
#if CHIP_KIND == 1
  // Clock/time register subset. Backup switchover and temperature are not modelled.
  uint64_t seconds=get_sim_nanos()/1000000000ULL;
  uint32_t day=(13*3600+20*60+seconds)%86400;
  if(reg==0)return bcd(day%60);if(reg==1)return bcd((day/60)%60);if(reg==2)return bcd(day/3600);
  if(reg==3)return 4;if(reg==4)return 0x18;if(reg==5)return 0x11;if(reg==6)return 0x26;
#endif
#if CHIP_KIND == 3
  // Programmed 5V contract result, not a CC/USB-PD physical negotiation.
  unsigned amps=attr_read(p->current_attr);
  uint8_t code=amps>=5?15:amps>=4?13:amps>=3?10:amps>=2?6:2;
  if(reg==0)return p->pd_requested?(0x10|code):0;
  if(reg==1)return p->pd_requested?0x48:0x40;
  if(reg==2)return 0x80|code;
#endif
  return p->regs[reg];
}
void chip_init(void) {
  peripheral *p=calloc(1,sizeof(*p));
  #if CHIP_KIND == 3
  p->vcc=pin_init("V+",OUTPUT_HIGH); // Ideal digital representation of the USB-C 5V startup rail.
#else
  p->vcc=pin_init("VCC",INPUT_PULLDOWN);
#endif
  p->ground=pin_init("GND",INPUT_PULLUP);
  p->first=true;
#if CHIP_KIND == 2
  p->oe=pin_init("OE",INPUT_PULLUP);p->supply=pin_init("VPLUS",INPUT_PULLDOWN);
  const char *pins[]={"PWM0","PWM1","PWM2"};
  for(int i=0;i<3;i++) {
    p->pwm[i]=pin_init(pins[i],OUTPUT_LOW);
    p->channels[i]=(pwm_channel){.dev=p,.channel=i,.high=false};
    timer_config_t timer={.callback=pulse,.user_data=&p->channels[i]};
    p->channels[i].timer=timer_init(&timer);timer_start(p->channels[i].timer,1000,false);
  }
  p->regs[0]=0x11;p->regs[254]=121;
  pin_watch_config_t watch={.edge=BOTH,.pin_change=output_disable,.user_data=p};pin_watch(p->oe,&watch);
#endif
#if CHIP_KIND == 3
  p->current_attr=attr_init("currentAmps",5);
#endif
  i2c_config_t bus={.address=CHIP_ADDRESS,.scl=pin_init("SCL",INPUT),.sda=pin_init("SDA",INPUT),
     .connect=connect_bus,.read=read_bus,.write=write_bus,.user_data=p};i2c_init(&bus);
}
