// GC9A01 240x240 circular framebuffer: DCS window/RGB565 subset, rotation 0.
// Vendor power/gamma commands are accepted but not electrically modelled.
#include "wokwi-api.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
typedef struct {pin_t cs,dc,vcc,gnd;spi_dev_t spi;buffer_t fb;uint8_t buffer[1],*rgba;
 uint32_t frame_width,frame_height;uint8_t command,args[4],index,high;bool half;uint16_t x0,x1,y0,y1,x,y;} lcd_model;
static void received(void *data,uint8_t *bytes,uint32_t count) {
 lcd_model *p=data;unsigned lo=p->frame_width*p->frame_height,hi=0;
 if(pin_read(p->vcc) && !pin_read(p->gnd))for(unsigned i=0;i<count;i++) {
  uint8_t byte=bytes[i];

  if(!pin_read(p->dc)) {p->command=byte;p->index=0;p->half=false;
    if(byte==0x2c){p->x=p->x0;p->y=p->y0;}continue;}
  if(p->command==0x2a || p->command==0x2b) {
   p->args[p->index++%4]=byte;
   if(p->index==4){unsigned a=(p->args[0]<<8)|p->args[1],b=(p->args[2]<<8)|p->args[3];
    if(p->command==0x2a){p->x0=a;p->x1=b;}else{p->y0=a;p->y1=b;}}
  }else if(p->command==0x2c) {
   if(!p->half){p->high=byte;p->half=true;continue;}
   p->half=false;unsigned rgb=(p->high<<8)|byte,x=p->x,y=p->y;
   int dx=(int)x*2-239,dy=(int)y*2-239;
   if(x<240 && y<240 && dx*dx+dy*dy<=240*240) {
    unsigned pos=(y+12)*p->frame_width+x+12,offset=pos*4;
    p->rgba[offset]=((rgb>>11)&31)*255/31;p->rgba[offset+1]=((rgb>>5)&63)*255/63;
    p->rgba[offset+2]=(rgb&31)*255/31;p->rgba[offset+3]=255;
    if(pos<lo)lo=pos;if(pos>hi)hi=pos;
   }
   if(++p->x>p->x1){p->x=p->x0;if(++p->y>p->y1)p->y=p->y0;}
  }
 }
 if(lo<p->frame_width*p->frame_height)buffer_write(p->fb,lo*4,p->rgba+lo*4,(hi-lo+1)*4);
 if(!pin_read(p->cs))spi_start(p->spi,p->buffer,sizeof(p->buffer));
}
static void selected(void *data,pin_t pin,uint32_t value) {
 lcd_model *p=data;if(value)spi_stop(p->spi);else spi_start(p->spi,p->buffer,sizeof(p->buffer));
}
void chip_init(void) {
 lcd_model *p=calloc(1,sizeof(*p));uint32_t width,height;
 p->fb=framebuffer_init(&width,&height);p->frame_width=width;p->frame_height=height;p->rgba=calloc(width*height,4);p->x1=239;p->y1=239;
 p->vcc=pin_init("VCC",INPUT_PULLDOWN);p->gnd=pin_init("GND",INPUT_PULLUP);
 // A 12-pixel presentation bezel surrounds the actual 240x240 controller RAM.
 // Opaque workspace-colour corners avoid Wokwi compositing transparency on black.
 for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++) {
  unsigned at=(y*width+x)*4;int dx=(int)x*2-263,dy=(int)y*2-263,r=dx*dx+dy*dy;
  unsigned red=51,green=51,blue=51;
  if(r<=260*260){red=85;green=117;blue=124;}
  if(r<=254*254){red=16;green=27;blue=35;}
  int ax=(int)x-12,ay=(int)y-12,adx=ax*2-239,ady=ay*2-239;
  if(ax>=0&&ax<240&&ay>=0&&ay<240&&adx*adx+ady*ady<=240*240){red=8;green=12;blue=16;}
  p->rgba[at]=red;p->rgba[at+1]=green;p->rgba[at+2]=blue;p->rgba[at+3]=255;
 }
 p->cs=pin_init("CS",INPUT_PULLUP);p->dc=pin_init("DC",INPUT);pin_init("RST",INPUT);
 spi_config_t config={.sck=pin_init("SCK",INPUT),.mosi=pin_init("SDA",INPUT),.miso=NO_PIN,.mode=0,.done=received,.user_data=p};
 p->spi=spi_init(&config);pin_watch_config_t watch={.edge=BOTH,.pin_change=selected,.user_data=p};pin_watch(p->cs,&watch);

 buffer_write(p->fb,0,p->rgba,width*height*4);
}
