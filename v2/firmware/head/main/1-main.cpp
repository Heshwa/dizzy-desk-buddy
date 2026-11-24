#include "device.hpp"
#include "calendar.hpp"
#include "face.h"
#include "motion.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <sys/time.h>
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

Settings settings{(1u<<0)|(1u<<7)|(1u<<9)|(1u<<20),{0x3,0x808080,0x101010},100,50,false,{}, {},0};
std::atomic<int> voice{Ready},reaction{DIZZY_FACE_IDLE},ringing{0};
std::atomic<int64_t> reaction_started{0},timer_at{0},watch_start{0},watch_value{0};
std::atomic<bool> record_requested{false},phone_connected{false},phone_playing{false},
    phone_discoverable{false},bridge_online{false},armed{false},floor_mode{false},motor_fault{false};
std::atomic<float> battery_voltage{0};
char status_text[100]{};
namespace {
std::recursive_mutex lock;
nvs_handle_t nvs;
int64_t launch_at, finish_at, head_return, arm_return;
int motion=DIZZY_REST;
std::atomic<bool> ready_io{false}, cut_switch{true};
std::array<float,8> angles{}, targets{};
uint32_t alarm_id=1;
Alarm active_alarm{};
int event_turn[3]={};
const char *const motion_names[]={"rest","wave","sway","heel","bounce","shuffle"};

cJSON *reply(bool ok,const char *error=nullptr,cJSON *value=nullptr) {
    cJSON *doc=cJSON_CreateObject(); cJSON_AddBoolToObject(doc,"ok",ok);
    if(error)cJSON_AddStringToObject(doc,"error",error);
    if(ok)cJSON_AddItemToObject(doc,"result",value?value:snapshot());
    return doc;
}
const cJSON *field(const cJSON *a,const char *key) {return cJSON_GetObjectItemCaseSensitive(a,key);}
const char *str(const cJSON *a,const char *key,const char *fallback=""){
    auto *item=field(a,key); return cJSON_IsString(item)?item->valuestring:fallback;
}
double num(const cJSON *a,const char *key,double fallback=NAN) {
    auto *item=field(a,key);return cJSON_IsNumber(item)?item->valuedouble:fallback;
}
bool flag(const cJSON *a,const char *key){return cJSON_IsTrue(field(a,key));}
bool between(double n,double lo,double hi){return std::isfinite(n)&&n>=lo&&n<=hi;}
bool same(const char *a,const char *b){return strcmp(a,b)==0;}
int64_t parse_date(const char *input) {
    tm day{};
    int y,m,d,h,min,sec,n=0;
    if(sscanf(input,"%4d-%2d-%2dT%2d:%2d:%2d%n",&y,&m,&d,&h,&min,&sec,&n)!=6 ||
       !between(y,2025,2099)||!between(m,1,12)||!between(d,1,31)||!between(h,0,23)||!between(min,0,59)||!between(sec,0,59))return 0;
    const char *zone=input+n;
    int offset=330,oh,om;
    if(same(zone,"Z")) offset=0;
    else if((*zone=='+'||*zone=='-')&&sscanf(zone+1,"%2d:%2d",&oh,&om)==2)
        offset=(*zone=='-'?-1:1)*(oh*60+om);
    else if(*zone) return 0;
    day.tm_year=y-1900;day.tm_mon=m-1;day.tm_mday=d;day.tm_hour=h;day.tm_min=min;day.tm_sec=sec;
    auto epoch=utc_seconds(day);
    gmtime_r(&epoch,&day);
    return day.tm_mon==m-1&&day.tm_mday==d?epoch-offset*60:0;
}
cJSON *alarms_json(){
    auto *list=cJSON_CreateArray();
    for(const auto &a:settings.alarms) if(a.at) {
        auto *row=cJSON_CreateObject();
        char id[12];snprintf(id,sizeof id,"%lu",(unsigned long)a.id);
        cJSON_AddStringToObject(row,"id",id);cJSON_AddStringToObject(row,"label",a.label);
        cJSON_AddNumberToObject(row,"at",a.at);cJSON_AddBoolToObject(row,"enabled",true);
        cJSON_AddItemToArray(list,row);
    }
    return list;
}
void stop_motion(){
    motion=DIZZY_REST;targets={};head_return=arm_return=0;
}
bool save_alarm(int64_t at,const char *label,uint8_t days) {
    for(auto &a:settings.alarms)if(!a.at){
        a.at=at;a.id=alarm_id++;a.weekdays=days;
        snprintf(a.label,sizeof a.label,"%s",label);save_settings();return true;
    }
    return false;
}
void alarms_tick(int64_t now){
    for(auto &a:settings.alarms) if(now>=a.at&&a.at>0){
        if(now-a.at<60&&!ringing){
            active_alarm=a;ringing=1;armed=false;stop_motion();
        }
        if(a.weekdays) {
            do {
                a.at+=86400;
                time_t local=a.at+19800;
                tm date{};
                gmtime_r(&local,&date);
                if(a.at>now && a.weekdays&(1<<((date.tm_wday+6)%7))) break;
                // Only a week of dates is needed after a long outage.
                if(a.at+604800<now) a.at+=((now-a.at)/604800)*604800;
            }while(true);
        }else a.at=0;
        save_settings();
    }
    if(timer_at>0&&now>=timer_at){
        timer_at=0;active_alarm={now,0,0,"Timer finished"};ringing=2;armed=false;stop_motion();
    }
}
}

int64_t milliseconds(){return esp_timer_get_time()/1000;}
void save_settings() {
    std::lock_guard<std::recursive_mutex> guard(lock);
    if(nvs){nvs_set_blob(nvs,"settings2",&settings,sizeof settings);nvs_commit(nvs);}
}
void show_reaction(int id) {reaction=id;reaction_started=milliseconds();}
void react(PetEvent event){
    std::lock_guard<std::recursive_mutex> guard(lock);
    uint32_t bits=settings.reactions[event]&0xffffff;
    int count=__builtin_popcount(bits);
    if(!count){show_reaction(0);return;}
    int choice=event_turn[event]++%count;
    for(int i=0;i<24;++i)if((bits>>i)&1u && choice--==0){show_reaction(i);return;}
}
// Clears a latched motor fault only when the robot is read as upright (same limit as local_arm),
// the stop switch is released, the I/O expander is ready and the battery is healthy.
// A failed or implausible IMU read keeps the fault latched.
bool clear_fault_if_safe(){
    std::lock_guard<std::recursive_mutex> guard(lock);
    float tilt=0;
    if(!ready_io||cut_switch||battery_voltage<6.8f||!board_imu(tilt)||tilt>12)return false;
    motor_fault=false;
    return true;
}
void latch_stop() {
    std::lock_guard<std::recursive_mutex> guard(lock);
    armed=false;floor_mode=false;motor_fault=true;stop_motion();
    board_servo(false,nullptr);
}
bool local_arm(){
#if CONFIG_DIZZY_ALLOW_FLOOR
    std::lock_guard<std::recursive_mutex> guard(lock);
    float tilt=0;
    if(!ready_io||cut_switch||ringing||settings.quiet||battery_voltage<6.8f||!board_imu(tilt)||tilt>12||
       (board_buttons() & (LeftFoot | RightFoot)) != (LeftFoot | RightFoot))return false;
    floor_mode=true;armed=true;motor_fault=false;
    return true;
#else
    return false;
#endif
}

void toggle_record(){
    const int current=voice.load();
    if(current==Recording) {
        record_requested=false;
        voice=Thinking;
    } else if(current==Ready || current==VoiceFault) {
        if(bridge_online) {
            voice=Recording;
            record_requested=true;
        }else {
            voice=VoiceFault;
            snprintf(status_text,sizeof status_text,"Mac voice bridge offline");
        }
    }
}

cJSON *snapshot(){
    std::lock_guard<std::recursive_mutex> guard(lock);
    auto *result=cJSON_CreateObject();
    cJSON_AddNumberToObject(result,"voice",voice);cJSON_AddNumberToObject(result,"face",reaction);
    cJSON_AddBoolToObject(result,"armed",armed);cJSON_AddBoolToObject(result,"fault",motor_fault);
    cJSON_AddBoolToObject(result,"quiet",settings.quiet);cJSON_AddNumberToObject(result,"bpm",settings.tempo);
    cJSON_AddNumberToObject(result,"volume",settings.volume/100.0);
    cJSON_AddBoolToObject(result,"phone_connected",phone_connected);cJSON_AddBoolToObject(result,"playing",phone_playing);
    cJSON_AddNumberToObject(result,"battery_voltage",battery_voltage);
    cJSON_AddStringToObject(result,"motion",motion_names[motion]);
    cJSON_AddItemToObject(result,"alarms",alarms_json());
    cJSON_AddNumberToObject(result,"timer_remaining",timer_at ? std::max<int64_t>(0,timer_at-time(nullptr)):0);
    cJSON_AddBoolToObject(result,"ringing",ringing!=0);
    return result;
}

cJSON *execute(const char *action,const cJSON *args){
    if(same(action,"music_control")||same(action,"phone_forget")||same(action,"local_pair")) {
        auto *requested=str(args,"command");
        const char *op=same(action,"phone_forget")?"FORGET":same(action,"local_pair")?"PAIR":
            same(requested,"play")?"PLAY":same(requested,"pause")?"PAUSE":
            same(requested,"next")?"NEXT":same(requested,"previous")?"PREVIOUS":nullptr;
        if(!op)return reply(false,"Choose play, pause, next or previous.");
        const char *ack=phone_command(op);
        if(same(ack,"QUEUED")) {
            auto *result=cJSON_CreateObject();
            cJSON_AddStringToObject(result,"status","Phone command sent; track change unconfirmed.");
            return reply(true,nullptr,result);
        }
        if(!same(ack,"OK"))return reply(false,same(ack,"DISCONNECTED")?"The phone is disconnected.":
            same(ack,"UNSUPPORTED")?"The phone does not support that control.":"The phone did not confirm the command.");
        return reply(true);
    }
    std::lock_guard<std::recursive_mutex> guard(lock);
    auto now=time(nullptr);
    if(same(action,"status"))return reply(true);
    if(same(action,"clock_read")){
        char iso[48]{};tm local{};localtime_r(&now,&local);
        strftime(iso,sizeof iso,"%Y-%m-%dT%H:%M:%S",&local);
        strlcat(iso,"+05:30",sizeof iso);
        auto *result=cJSON_CreateObject();
        if(now<1700000000){cJSON_Delete(result);return reply(false,"Set the clock by connecting the Mac bridge.");}
        cJSON_AddStringToObject(result,"time",iso);return reply(true,nullptr,result);
    }
    if(same(action,"alarm_list")){
        auto *result=cJSON_CreateObject();cJSON_AddItemToObject(result,"alarms",alarms_json());
        return reply(true,nullptr,result);
    }
    if(same(action,"alarm_set")||same(action,"alarm_add_minutes")){
        if(now<1700000000)return reply(false,"Set the clock by connecting the Mac bridge.");
        double minutes=num(args,"minutes");
        auto at=same(action,"alarm_set")?parse_date(str(args,"at")):
            between(minutes,.05,1440)?now+(int64_t)(minutes*60):0;
        if(at<=now)return reply(false,"Choose a future time with AM or PM.");
        uint8_t days=0;
        const cJSON *day=nullptr;
        cJSON_ArrayForEach(day,field(args,"weekdays")){
            if(!cJSON_IsNumber(day)||day->valueint<0||day->valueint>6)return reply(false,"Choose valid weekdays.");
            days|=1<<day->valueint;
        }
        if(!save_alarm(at,str(args,"label","Alarm"),days))return reply(false,"Alarm list is full.");
    }else if(same(action,"alarm_cancel")){
        const auto id=strtoul(str(args,"id"),nullptr,10);
        bool removed=false;
        for(auto &a:settings.alarms)if(a.at&&a.id==id){a={};removed=true;}
        if(!removed)return reply(false,"Alarm ID was not found.");
        save_settings();
    }else if(same(action,"alarm_dismiss"))ringing=0;
    else if(same(action,"alarm_snooze")){
        if(!ringing)return reply(false,"No alarm is ringing.");
        double minutes=num(args,"minutes",5);
        if(!between(minutes,1,60)||!save_alarm(now+(int64_t)(minutes*60),active_alarm.label,0))
            return reply(false,"Choose a shorter snooze or remove a saved alarm.");
        ringing=0;
    }else if(same(action,"timer_cancel"))timer_at=0;
    else if(same(action,"timer_check")){
        auto *result=cJSON_CreateObject();
        cJSON_AddNumberToObject(result,"seconds_remaining",timer_at ? std::max<int64_t>(0,timer_at-now):0);
        return reply(true,nullptr,result);
    }else if(same(action,"timer_start")||same(action,"focus_start")){
        double duration=same(action,"focus_start")?num(args,"minutes",25)*60:num(args,"seconds");
        if(!between(duration,1,86400))return reply(false,"Choose a valid timer duration.");
        timer_at=now+(int64_t)duration;
    }else if(same(action,"quiet_set")){
        if(!cJSON_IsBool(field(args,"enabled"))) return reply(false,"Choose whether quiet mode is enabled.");
        settings.quiet=flag(args,"enabled");
        if(settings.quiet){armed=false;stop_motion();}
        save_settings();
    }else if(same(action,"volume_set")){
        double level=num(args,"level");
        if(!between(level,0,1))return reply(false,"Volume must be between 0 and 1.");
        settings.volume=lround(level*100);save_settings();
    }else if(same(action,"head_turn")||same(action,"head_pitch")||same(action,"arm_lift")||same(action,"arms_pose")||same(action,"motion_play")){
#if CONFIG_DIZZY_ALLOW_MOTORS
        if(!ready_io||motor_fault||cut_switch||battery_voltage<6.8f||settings.quiet||ringing)
            return reply(false,"Motion is locked. Check power and the local controls.");
        if(same(action,"head_turn")||same(action,"head_pitch")){
            const bool yaw=same(action,"head_turn");
            double degree=num(args,"degrees");
            if(!between(degree,yaw?-45:-20,yaw?45:25))return reply(false,"Head angle exceeds its limits.");
            motion=DIZZY_REST;targets[yaw?0:1]=degree;
            head_return=flag(args,"temporary")?milliseconds()+2000:0;
            auto *move=cJSON_CreateObject();
            cJSON_AddNumberToObject(move,"requested_degrees",degree);
            cJSON_AddStringToObject(move,"status","Angle command accepted. This servo does not report its position.");
            return reply(true,nullptr,move);
        }else if(same(action,"arm_lift")){
            const char *side=str(args,"side");
            double degree=num(args,"degrees",65);
            if((!same(side,"left")&&!same(side,"right"))||!between(degree,0,90))return reply(false,"Choose a side and an angle of at most 90 degrees.");
            motion=DIZZY_REST;targets[same(side,"left")?2:3]=degree;
            arm_return=milliseconds()+2000;
        }else {
            const char *choice=same(action,"arms_pose")?str(args,"pose"):str(args,"name");
            if(same(choice,"rest"))stop_motion();
            else if(same(choice,"lift")||same(choice,"happy")||same(choice,"hello")||same(choice,"goodnight")){
                motion=DIZZY_REST;targets[2]=targets[3]=same(choice,"lift")?75:30;
                arm_return=milliseconds()+2000;
            }else{
                int selected=0;
                for(int i=1;i<6;++i)if(same(choice,motion_names[i]))selected=i;
                if(!selected)return reply(false,"Unknown dance or wave.");
                if(selected>DIZZY_WAVE&&(!armed||!floor_mode))return reply(false,"Arm floor motion on the robot first.");
                double seconds=num(args,"seconds",selected==DIZZY_SHUFFLE?1200.0/settings.tempo:selected==DIZZY_WAVE?3:60);
                if(!between(seconds,1,60))return reply(false,"Choose a duration of 1–60 seconds.");
                motion=selected;launch_at=milliseconds();finish_at=launch_at+(int64_t)(seconds*1000);
            }
        }
#else
        return reply(false,"Motor outputs are disabled until bench validation.");
#endif
    }else if(same(action,"motion_stop")){
        stop_motion();armed=false;floor_mode=false;
    }else if(same(action,"voice_state")){
        auto *state=str(args,"state");
        if(same(state,"idle"))voice=Ready;
        else if(same(state,"thinking"))voice=Thinking;
        else if(same(state,"speaking"))voice=Speaking;
        else if(same(state,"fault"))voice=VoiceFault;
        else return reply(false,"Unknown voice state.");
    }else if(same(action,"expression_set")){
        auto *face=str(args,"expression");
        if(same(face,"happy"))react(Petted);
        else if(same(face,"heart")||same(face,"goodnight"))react(Greeted);
        else if(same(face,"sleepy"))show_reaction(5);
        else if(same(face,"blink"))show_reaction(3);
        else return reply(false,"Choose a known expression.");
    }else if(same(action,"reaction_assign")||same(action,"favorites_set")){
        auto *ids=field(args,"ids");uint32_t mask=0;
        if(!cJSON_IsArray(ids))return reply(false,"Select reactions from the library.");
        const cJSON *id=nullptr;
        cJSON_ArrayForEach(id,ids) {
            if(!cJSON_IsNumber(id)||!between(id->valuedouble,0,23)||id->valueint!=id->valuedouble)
                return reply(false,"Choose a reaction from 0–23.");
            mask|=1u<<id->valueint;
        }
        if(same(action,"favorites_set"))settings.favorites=mask;
        else{
            const char *event=str(args,"event");
            int index=same(event,"pet")?0:same(event,"greeting")?1:same(event,"win")?2:-1;
            if(index<0||!mask)return reply(false,"Choose an event and at least one reaction.");
            settings.reactions[index]=mask;event_turn[index]=0;
        }
        save_settings();
    }else if(same(action,"face_preview")){
        double id=num(args,"id");
        if(!between(id,0,23)||id!=floor(id))return reply(false,"Choose a reaction from 0–23.");
        show_reaction(id);
    }else if(same(action,"receive_greeting")){
        react(Greeted);
    }else if(same(action,"stopwatch")){
        const char *command=str(args,"command");
        if(same(command,"start")&&!watch_start)watch_start=milliseconds();
        else if(same(command,"stop")&&watch_start){watch_value+=milliseconds()-watch_start;watch_start=0;}
        else if(same(command,"reset")){watch_start=0;watch_value=0;}
    }else return reply(false,"This action is unavailable on the prototype.");
    return reply(true);
}

extern "C" void app_main(){
    auto err=nvs_flash_init();
    if(err==ESP_ERR_NVS_NO_FREE_PAGES||err==ESP_ERR_NVS_NEW_VERSION_FOUND){nvs_flash_erase();err=nvs_flash_init();}
    ESP_ERROR_CHECK(err);
    if(nvs_open("dizzy_v2",NVS_READWRITE,&nvs)==ESP_OK){
        size_t size=sizeof settings;
        nvs_get_blob(nvs,"settings2",&settings,&size);
    }
    for(const auto &a:settings.alarms)alarm_id=std::max(alarm_id,a.id+1);
    setenv("TZ","IST-5:30",1);tzset();
    ready_io=board_init();
    const auto rtc=board_rtc_read();
    if(rtc>1700000000){timeval current{rtc,0};settimeofday(&current,nullptr);}
    phone_setup();setup_interface();setup_network();
    uint8_t previous=0, last=0;
    int64_t pad_at=0, tap_at=0, read_at=0;
    time_t seen=0;
    int last_gain=-1;
    while(true){
        const auto t=milliseconds();
        uint8_t raw=board_buttons();
        if(raw==last&&raw!=previous) {
            uint8_t rise=raw&~previous, fall=previous&~raw;
            cut_switch=raw&StopKey;
            if(rise&Talk)toggle_record();
            if(rise&ArmKey) {
                if(floor_mode){armed=false;floor_mode=false;}
                else if(!local_arm() && clear_fault_if_safe()) {
                    // Physical key can clear a stop for guarded upper-body use, but only
                    // after a fresh upright IMU reading and a healthy battery (see clear_fault_if_safe).
                }
            }
            if(rise&StopKey)latch_stop();
            if(rise&(LeftPad|RightPad)){
                if(ringing){auto *a=execute("alarm_snooze",nullptr);cJSON_Delete(a);}
                else pad_at=t;
            }
            if((fall&(LeftPad|RightPad))&&!(raw&(LeftPad|RightPad))&&pad_at){
                if(t-pad_at>=1200){request_gesture("goodnight");tap_at=0;}
                else if(tap_at&&t-tap_at<350){request_gesture("wave");tap_at=0;}
                else tap_at=t;
                pad_at=0;
            }
            previous=raw;
        }
        last=raw;
        if(tap_at&&t-tap_at>=350){react(Petted);tap_at=0;}
        if(t-read_at>=100){
            read_at=t; battery_voltage=board_battery();
            if(armed){
                float tilt=0;
                if(!board_imu(tilt)||tilt>38||battery_voltage<6.8f)latch_stop();
            }
        }
        const auto now=time(nullptr);
        if(now!=seen){std::lock_guard<std::recursive_mutex> guard(lock);alarms_tick(now);seen=now;}
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            if(motion!=DIZZY_REST&&t>=finish_at)stop_motion();
            if(motion>DIZZY_WAVE&&!armed)stop_motion();
            if(arm_return&&t>=arm_return){targets[2]=targets[3]=0;arm_return=0;}
            if(head_return&&t>=head_return){targets[0]=targets[1]=0;head_return=0;}
            auto target=targets;
            if(motion!=DIZZY_REST)dizzy_pose(motion,(t-launch_at)/1000.0,settings.tempo,target.data());
            for(int axis=0;axis<8;++axis)angles[axis]+=std::clamp(target[axis]-angles[axis],-1.8f,1.8f);
#if CONFIG_DIZZY_ALLOW_MOTORS
            board_servo(ready_io&&!cut_switch&&!motor_fault&&battery_voltage>=6.8f,angles.data());
#else
            board_servo(false,nullptr);
#endif
            int gain=settings.quiet?0:voice!=Ready||ringing?settings.volume*15/100:settings.volume;
            if(t%1000<25 || gain!=last_gain) { phone_command("GAIN",gain,false);last_gain=gain; }
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
