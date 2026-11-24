#include "device.hpp"
#include "calendar.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

extern "C" {
#include "bmi270.h"
}

namespace {
constexpr int PCA=0x40, IO=0x20, ADC=0x48, RTC=0x68, IMU=0x69;
constexpr auto enable_pin=GPIO_NUM_16;
constexpr uart_port_t phone_uart=UART_NUM_0;
i2c_master_dev_handle_t devices[128]{};
bmi2_dev imu{};
bool imu_ready=false;
QueueHandle_t responses;
SemaphoreHandle_t command_lock;
struct Ack { int id; char status[20]; };
int sequence=0;

bool read(int address,uint8_t reg,uint8_t *out,size_t n) {
    return devices[address] && i2c_master_transmit_receive(devices[address],&reg,1,out,n,12)==ESP_OK;
}
bool write(int address,uint8_t reg,const uint8_t *in,size_t n){
    uint8_t buffer[65];
    if(n>64||!devices[address]) return false;
    buffer[0]=reg; memcpy(buffer+1,in,n);
    return i2c_master_transmit(devices[address],buffer,n+1,12)==ESP_OK;
}
bool reg(int address,uint8_t index,uint8_t value) { return write(address,index,&value,1); }
int8_t imu_read(uint8_t reg,uint8_t *data,uint32_t len,void *) { return read(IMU,reg,data,len)?0:-1; }
int8_t imu_write(uint8_t reg,const uint8_t *data,uint32_t len,void *) { return write(IMU,reg,data,len)?0:-1; }
void imu_delay(uint32_t us,void *) {
    if(us>=1000) vTaskDelay(pdMS_TO_TICKS(us/1000)+1);
    else esp_rom_delay_us(us);
}
int bcd(uint8_t value) {return 10*(value>>4)+(value&15);}
uint8_t to_bcd(int value) {return (uint8_t)((value/10)<<4 | (value%10));}

void receive_phone(void *) {
    char line[80]={}; size_t size=0;
    int64_t last=0;
    while(true) {
        char ch;
        if(uart_read_bytes(phone_uart,&ch,1,pdMS_TO_TICKS(40))==1) {
            if(ch=='\n') {
                line[size]=0; size=0;
                Ack response{};
                int connected,playing,discoverable;
                if(sscanf(line,"STATE %d %d %d",&connected,&playing,&discoverable)==3) {
                    phone_connected=connected; phone_playing=playing; phone_discoverable=discoverable; last=milliseconds();
                } else if(sscanf(line,"ACK %d %19s",&response.id,response.status)==2)
                    xQueueSend(responses,&response,0);
            } else if(ch!='\r'&&size<sizeof line-1) line[size++]=ch;
        }
        if(milliseconds()-last>3000) {phone_connected=false;phone_playing=false;phone_discoverable=false;}
    }
}
}

bool board_init() {
    gpio_config_t oe{};
    oe.pin_bit_mask=1ULL<<enable_pin;oe.mode=GPIO_MODE_OUTPUT_OD;oe.pull_up_en=GPIO_PULLUP_ENABLE;
    gpio_config(&oe);gpio_set_level(enable_pin,1);
    i2c_master_bus_config_t conf{};
    conf.i2c_port=I2C_NUM_1;conf.sda_io_num=GPIO_NUM_17;conf.scl_io_num=GPIO_NUM_18;
    conf.clk_source=I2C_CLK_SRC_DEFAULT;conf.glitch_ignore_cnt=7;
    i2c_master_bus_handle_t bus;
    if(i2c_new_master_bus(&conf,&bus)!=ESP_OK)return false;
    for(int address:{PCA,IO,ADC,RTC,IMU}) {
        i2c_device_config_t target{};
        target.dev_addr_length=I2C_ADDR_BIT_LEN_7;target.device_address=address;target.scl_speed_hz=100000;
        i2c_master_bus_add_device(bus,&target,&devices[address]);
    }
    bool pwm=reg(PCA,0x00,0x30) && reg(PCA,0xfe,121) && reg(PCA,0x01,0x04) && reg(PCA,0x00,0x20);
    bool controls=reg(IO,0x00,0xff) && reg(IO,0x0c,0xff);
    uint8_t ignored[2];
    const bool power=read(ADC,0x01,ignored,2);
    imu.read=imu_read;imu.write=imu_write;imu.delay_us=imu_delay;
    imu.intf=BMI2_I2C_INTF;imu.read_write_len=32;
    uint8_t sensor=BMI2_ACCEL;
    imu_ready=bmi270_init(&imu)==BMI2_OK && bmi270_sensor_enable(&sensor,1,&imu)==BMI2_OK;
    return pwm && controls && power;
}

uint8_t board_buttons() {
    uint8_t buttons;
    if(!read(IO,0x12,&buttons,1)) return StopKey;
    return (uint8_t)~buttons;
}

void board_servo(bool enabled,const float *angles) {
    if (!enabled) {
        gpio_set_level(enable_pin,1);
        return;
    }
    uint8_t data[32]{};
    constexpr int direction[]={-1,1,1,-1,1,-1,1,-1};
    for(int i=0;i<8;++i){
        float degree=std::clamp(settings.trim[i]+direction[i]*angles[i],-90.f,90.f);
        int tick=std::lround((1500+degree*9.2f)*4096/20000);
        const int leading=i*256;
        const int trailing=(leading+tick)&4095;
        data[i*4]=leading&255;data[i*4+1]=(leading>>8)&15;
        data[i*4+2]=trailing&255;data[i*4+3]=(trailing>>8)&15;
        if(i>=4&&!armed)data[i*4+3]=0x10;
    }
    gpio_set_level(enable_pin,write(PCA,0x06,data,sizeof data)?0:1);
}

bool board_imu(float &tilt) {
    if(!imu_ready) return false;
    bmi2_sens_data data{};
    if(bmi2_get_sensor_data(&data,&imu)!=BMI2_OK)return false;
    float x=data.acc.x,y=data.acc.y,z=data.acc.z;
    float mag=sqrtf(x*x+y*y+z*z);
    if(mag<100) return false;
    tilt=acosf(std::clamp(z/mag,-1.f,1.f))*57.29578f;
    return true;
}

float board_battery() {
    // ADS1115 A0, ground-referenced, ±4.096 V. Allow conversions with no busy waiting.
    static bool configured=false;
    if(!configured){
        const uint8_t config[]={0xC2,0xA3};
        configured=write(ADC,1,config,2);
        return 0;
    }
    uint8_t data[2];
    if(!read(ADC,0,data,2))return 0;
    return (int16_t)((data[0]<<8)|data[1]) * 0.000125f * 4.f;
}

time_t board_rtc_read() {
    uint8_t data[7],status;
    if(!read(RTC,0x0f,&status,1)||status&0x80||!read(RTC,0,data,7))return 0;
    tm date{};
    date.tm_sec=bcd(data[0]&0x7f);date.tm_min=bcd(data[1]&0x7f);
    date.tm_hour=bcd(data[2]&0x3f);date.tm_mday=bcd(data[4]&0x3f);
    date.tm_mon=bcd(data[5]&0x1f)-1;date.tm_year=100+bcd(data[6]);date.tm_isdst=0;
    return utc_seconds(date);
}

bool board_rtc_set(time_t time){
    tm date{};
    gmtime_r(&time,&date);
    uint8_t data[]={to_bcd(date.tm_sec),to_bcd(date.tm_min),to_bcd(date.tm_hour),
        to_bcd(date.tm_wday+1),to_bcd(date.tm_mday),to_bcd(date.tm_mon+1),to_bcd(date.tm_year-100)};
    uint8_t status;
    return write(RTC,0,data,7) && read(RTC,0x0f,&status,1) && reg(RTC,0x0f,status&0x7f);
}

void phone_setup() {
    uart_config_t config{};
    config.baud_rate=115200;config.data_bits=UART_DATA_8_BITS;config.parity=UART_PARITY_DISABLE;
    config.stop_bits=UART_STOP_BITS_1;config.flow_ctrl=UART_HW_FLOWCTRL_DISABLE;config.source_clk=UART_SCLK_DEFAULT;
    if(uart_param_config(phone_uart,&config)!=ESP_OK ||
       uart_set_pin(phone_uart,43,44,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE)!=ESP_OK ||
       uart_driver_install(phone_uart,1024,0,0,nullptr,0)!=ESP_OK) return;
    responses=xQueueCreate(8,sizeof(Ack));
    command_lock=xSemaphoreCreateMutex();
    xTaskCreate(receive_phone,"phone-uart",3072,nullptr,5,nullptr);
}

const char *phone_command(const char *command,int value,bool wait) {
    if(!command_lock) return "OFFLINE";
    if(xSemaphoreTake(command_lock,wait?pdMS_TO_TICKS(1800):0)!=pdTRUE)return "BUSY";
    const int id=wait?++sequence:0;
    char line[64];
    int bytes=snprintf(line,sizeof line,"%d %s %d\n",id,command,value);
    uart_write_bytes(phone_uart,line,bytes);
    thread_local static char result[20];
    const char *reply=wait?"OFFLINE":"OK";
    int64_t until=milliseconds()+1500;
    while(wait && milliseconds()<until) {
        Ack ack{};
        if(xQueueReceive(responses,&ack,pdMS_TO_TICKS(40)) && ack.id==id){
            memcpy(result,ack.status,sizeof result);
            reply=result;
            break;
        }
    }
    xSemaphoreGive(command_lock);
    return reply;
}
