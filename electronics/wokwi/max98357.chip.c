#include "wokwi-api.h"
void chip_init(void) {
  pin_init("VIN",INPUT);
  pin_init("GND",INPUT);
  pin_init("BCLK",INPUT);
  pin_init("LRC",INPUT);
  pin_init("DIN",INPUT);
  pin_init("GAIN",INPUT);
  pin_init("SD",INPUT);
  pin_init("SPK+",INPUT);
  pin_init("SPK-",INPUT);
}
