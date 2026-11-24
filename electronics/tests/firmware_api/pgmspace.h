#pragma once
#include <stdint.h>
#define PROGMEM
inline uint8_t pgm_read_byte(const void *p){return *(const uint8_t*)p;}
