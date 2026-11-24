#include "wokwi-api.h"
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>

typedef struct {
  uint8_t address, pointer, offset;
  bool first;
  pin_t power, ground, inputs[7];
} device;

static bool connected(void *data,uint32_t address,bool read) {
  device *d=data;
  d->offset=0;
  if(!read)d->first=true;
  return pin_read(d->power)&&!pin_read(d->ground);
}
static bool writing(void *data,uint8_t value) {
  device *d=data;
  if(d->first){d->pointer=value;d->first=false;}
  return true;
}
static uint8_t reading(void *data) {
  device *d=data;
  uint8_t offset=d->offset++;
  if(d->address==0x20 && d->pointer==0x12) {
    uint8_t result=255;
    for(int i=0;i<5;++i)if(!pin_read(d->inputs[i]))result&=~(1<<i);
    return result;
  }
  if(d->address==0x48 && d->pointer==0x00) {
    uint16_t raw=pin_read(d->inputs[5])?14880:12600;
    return offset?raw&255:raw>>8;
  }
  if(d->address==0x69 && d->pointer==0x0c){
    /* Accelerometer register test fixture: upright or horizontal at 1 g. */
    bool tilt=!pin_read(d->inputs[6]);
    return offset==(tilt?1:5)?0x40:0;
  }
  if(d->address==0x69&&d->pointer==0x00)return 0x24;
  return 0;
}
void chip_init(void) {
  const char *keys[]={"TALK","CROWN_L","CROWN_R","ARM","STOP","LOW_BAT","TILT"};
  pin_t inputs[7];
  for(int i=0;i<7;i++)inputs[i]=pin_init(keys[i],INPUT_PULLUP);
  pin_t scl=pin_init("SCL",INPUT),sda=pin_init("SDA",INPUT);
  pin_t power=pin_init("VCC",INPUT_PULLDOWN),ground=pin_init("GND",INPUT_PULLUP);
  uint8_t addresses[]={0x20,0x48,0x69};
  for(int i=0;i<3;++i) {
    device *d=calloc(1,sizeof(device));
    d->address=addresses[i];d->power=power;d->ground=ground;
    for(int j=0;j<7;++j)d->inputs[j]=inputs[j];
    i2c_config_t bus={.address=d->address,.scl=scl,.sda=sda,.connect=connected,.read=reading,.write=writing,.user_data=d};
    i2c_init(&bus);
  }
}
