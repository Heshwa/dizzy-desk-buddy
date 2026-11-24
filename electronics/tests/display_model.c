#include "wokwi-api.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int values[32],np;static uint8_t frame[264*264*4];static spi_config_t spi;
pin_t pin_init(const char*n,int m){values[++np]=m==INPUT_PULLUP||m==OUTPUT_HIGH;return np;}
uint32_t pin_read(pin_t p){return values[p];}void pin_write(pin_t p,uint32_t v){values[p]=v;}
void pin_watch(pin_t p,const pin_watch_config_t*w){}
spi_dev_t spi_init(const spi_config_t*c){spi=*c;return 1;}void spi_start(spi_dev_t d,uint8_t*b,uint32_t n){}void spi_stop(spi_dev_t d){}
buffer_t framebuffer_init(uint32_t*w,uint32_t*h){*w=*h=264;return 1;}
void buffer_write(buffer_t b,uint32_t o,const void*v,uint32_t n){assert(o+n<=sizeof(frame));memcpy(frame+o,v,n);}
#include "../wokwi/gc9a01.chip.c"
static void command(lcd_model*p,uint8_t c){values[p->dc]=0;received(p,&c,1);values[p->dc]=1;}
static void window(lcd_model*p,uint16_t x,uint16_t y){uint8_t a[4]={x>>8,x&255,x>>8,x&255};command(p,0x2a);received(p,a,4);a[0]=a[2]=y>>8;a[1]=a[3]=y&255;command(p,0x2b);received(p,a,4);command(p,0x2c);}
int main(void){chip_init();lcd_model*p=spi.user_data;values[p->vcc]=1;values[p->gnd]=0;values[p->cs]=0;
 window(p,120,120);uint8_t red[2]={0xf8,0};received(p,red,1);assert(p->half);received(p,red+1,1);
 unsigned at=(132*264+132)*4;assert(frame[at]==255&&frame[at+1]==0&&frame[at+2]==0&&frame[at+3]==255);
 window(p,0,0);received(p,red,2);assert(frame[0]==51&&frame[1]==51&&frame[2]==51&&frame[3]==255);
 unsigned corner=(12*264+12)*4;assert(frame[corner]!=255);
 values[p->vcc]=0;window(p,120,120);uint8_t green[2]={7,0xe0};received(p,green,2);assert(frame[at]==255);
 puts("PASS LCD RGB565 pixels, split-byte transfer, circular clipping and missing-power inhibit");}
