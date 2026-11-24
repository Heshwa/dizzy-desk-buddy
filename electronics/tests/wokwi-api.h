// Host test double for the documented Wokwi API. No electrical simulation.
#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef int pin_t;
typedef int timer_t;
#define LOW 0
#define HIGH 1
#define INPUT 0
#define INPUT_PULLUP 1
#define INPUT_PULLDOWN 2
#define OUTPUT_LOW 3
#define OUTPUT_HIGH 4
#define BOTH 3
typedef struct {void (*callback)(void*);void *user_data;} timer_config_t;
typedef struct {int edge;void (*pin_change)(void*,pin_t,uint32_t);void *user_data;} pin_watch_config_t;
typedef struct {uint32_t address;pin_t scl,sda;bool (*connect)(void*,uint32_t,bool);uint8_t (*read)(void*);bool (*write)(void*,uint8_t);void*user_data;} i2c_config_t;
pin_t pin_init(const char*,int);uint32_t pin_read(pin_t);void pin_write(pin_t,uint32_t);
timer_t timer_init(const timer_config_t*);void timer_start(timer_t,uint32_t,bool);
void pin_watch(pin_t,const pin_watch_config_t*);void i2c_init(const i2c_config_t*);
uint32_t attr_init(const char*,uint32_t);uint32_t attr_read(uint32_t);uint64_t get_sim_nanos(void);

#define NO_PIN (-1)
typedef int spi_dev_t;typedef int buffer_t;
typedef struct {pin_t sck,mosi,miso;uint32_t mode;void(*done)(void*,uint8_t*,uint32_t);void*user_data;}spi_config_t;
spi_dev_t spi_init(const spi_config_t*);void spi_start(spi_dev_t,uint8_t*,uint32_t);void spi_stop(spi_dev_t);
buffer_t framebuffer_init(uint32_t*,uint32_t*);void buffer_write(buffer_t,uint32_t,const void*,uint32_t);
