// Wiring placeholder; no acoustic, impedance or I2S simulation.
#include "wokwi-api.h"
void chip_init(void){pin_init("PLUS",INPUT);pin_init("MINUS",INPUT);}
