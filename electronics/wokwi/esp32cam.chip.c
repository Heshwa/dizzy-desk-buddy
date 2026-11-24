#include "wokwi-api.h"
void chip_init(void) {
  pin_init("5V",INPUT);
  pin_init("GND",INPUT);
}
