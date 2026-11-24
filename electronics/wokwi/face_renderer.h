#pragma once
// Bitmaps come from the same renderer as Webots; only changed horizontal spans
// are sent over SPI. Flash masks avoid allocating full RGB565 frames on ESP32.
static const uint8_t *previousBody=nullptr;
static uint8_t previousLabel[LABEL_BYTES]={0},nextLabel[LABEL_BYTES]={0};
static bool maskPixel(const uint8_t *data,int stride,int x,int y) {
 return data && (pgm_read_byte(data+y*stride+x/8)&(128>>(x&7)));
}
static void drawMaskDelta(const uint8_t *oldMask,const uint8_t *newMask,int x0,int y0,int width,int height) {
 int stride=(width+7)/8;
 for(int y=0;y<height;y++)for(int x=0;x<width;) {
  bool oldPixel=maskPixel(oldMask,stride,x,y),newPixel=maskPixel(newMask,stride,x,y);
  if(oldPixel==newPixel){x++;continue;}
  int start=x++;
  while(x<width && maskPixel(oldMask,stride,x,y)!=maskPixel(newMask,stride,x,y) && maskPixel(newMask,stride,x,y)==newPixel)x++;
  lcd.drawFastHLine(x0+start,y0+y,x-start,newPixel?FACE_INK:FACE_BACKGROUND);
 }
}
static FaceMode selectedFace(uint32_t now) {
 if(ringing)return FACE_ALARM;
 if(listening)return FACE_LISTENING;
 if((int32_t)(previewUntil-now)>0)return previewFace;
 if((int32_t)(happyUntil-now)>0)return FACE_HAPPY;
 return now-lastActivity>=30000?FACE_SLEEPY:FACE_IDLE;
}
static void composeClock(const char *clock) {
 int advance=0;
 for(int i=0;i<5;i++)advance+=CLOCK_GLYPHS[clock[i]==':'?10:clock[i]-'0'].advance;
 int width=(advance+32)/64,x64=((240-width)/2)*64;
 for(int i=0;i<5;i++) {
  const ClockGlyph &g=CLOCK_GLYPHS[clock[i]==':'?10:clock[i]-'0'];
  int x0=(x64+32)/64+g.left;
  for(int y=0;y<g.height;y++)for(int x=0;x<g.width;x++)if(maskPixel(CLOCK_BITS+g.offset,(g.width+7)/8,x,y)) {
   int px=x0+x,py=g.top+y;
   if(px>=0&&px<240&&py>=0&&py<LABEL_H)nextLabel[py*30+px/8]|=128>>(px&7);
  }
  x64+=g.advance;
 }
}
void drawFace() {
 uint32_t now=millis();FaceMode mode=selectedFace(now);const FaceGroup &group=FACE_GROUPS[mode];
 bool blink=false; // Explicit FACE_BLINK only; match the shared Webots renderer.
 unsigned phase=group.count>1?(now/(mode==FACE_MUSIC?63:90))%group.count:0;
 const uint8_t *body=FACE_FRAMES[group.start+(blink?group.count:0)+phase];
 if(body!=previousBody){drawMaskDelta(previousBody,body,FACE_X,FACE_Y,FACE_W,FACE_H);previousBody=body;}
 int hour=readReg(0x68,2),minute=readReg(0x68,1);char clock[6]="00:00";
 bool clockOK=hour>=0&&minute>=0;
 if(clockOK)snprintf(clock,sizeof clock,"%02d:%02d",((hour>>4)&3)*10+(hour&15),(minute>>4)*10+(minute&15));
 int label=mode==FACE_GOODNIGHT?0:mode==FACE_LISTENING?1:mode==FACE_THINKING?2:mode==FACE_SPEAKING?3:mode==FACE_ALARM?4:!powerOK?5:!clockOK?6:-1;
 static int previousLabelId=-99;static char oldClock[6]="";
 if(label!=previousLabelId || (label==-1 && strcmp(clock,oldClock))) {
  memset(nextLabel,0,sizeof nextLabel);
  if(label>=0)for(int i=0;i<LABEL_BYTES;i++)nextLabel[i]=pgm_read_byte(FACE_LABELS[label]+i);else composeClock(clock);
  drawMaskDelta(previousLabel,nextLabel,0,LABEL_Y,240,LABEL_H);
  memcpy(previousLabel,nextLabel,sizeof nextLabel);previousLabelId=label;strcpy(oldClock,clock);
 }
}
