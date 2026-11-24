#pragma once
#include <atomic>
#include <cstdint>
#include <ctime>
#include "cJSON.h"

enum Input { Talk=1, LeftPad=2, RightPad=4, ArmKey=8, StopKey=16, LeftFoot=32, RightFoot=64 };
enum VoiceState { Ready, Recording, Thinking, Speaking, VoiceFault };
enum PetEvent { Petted, Greeted, Won };
struct Alarm { int64_t at; uint32_t id; uint8_t weekdays; char label[32]; };
struct Settings {
    uint32_t favorites;
    uint32_t reactions[3];
    int tempo;
    int volume;
    bool quiet;
    float trim[8];
    Alarm alarms[12];
    int clock_style;
};
extern Settings settings;
extern std::atomic<int> voice;
extern std::atomic<bool> record_requested;
extern std::atomic<bool> phone_connected, phone_playing, phone_discoverable, bridge_online;
extern std::atomic<bool> armed, floor_mode, motor_fault;
extern std::atomic<int64_t> timer_at, watch_start, watch_value;
extern std::atomic<float> battery_voltage;
extern std::atomic<int> reaction, ringing;
extern std::atomic<int64_t> reaction_started;
extern char status_text[100];

bool board_init();
uint8_t board_buttons();
void board_servo(bool enabled, const float *angles);
bool board_imu(float &tilt);
float board_battery();
time_t board_rtc_read();
bool board_rtc_set(time_t time);
void phone_setup();
const char *phone_command(const char *command,int value=0,bool wait=true);
void save_settings();
void show_reaction(int id);
void react(PetEvent event);
void toggle_record();
void latch_stop();
bool local_arm();
void setup_interface();
void setup_network();
void request_gesture(const char *gesture);
int64_t milliseconds();
cJSON *execute(const char *action,const cJSON *args);
cJSON *snapshot();
