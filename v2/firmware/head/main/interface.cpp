#include "device.hpp"
#include "face_lvgl.hpp"
#include "bsp/esp32_s3_touch_amoled_1_75.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace {
DizzyFaceView face;
lv_obj_t *clock_label,*mode_label,*page,*message;
int catalog_at=0, category=0, picked_event=0, tool_page=0;
int game=0, game_step=0, game_hits=0, game_round=0;
int64_t game_started=0, cue_at=0;
uint8_t sequence[4]{};
bool cue_used=false;
const char *events[]={"Petting","Greeting","Game win"};
const char *event_keys[]={"pet","greeting","win"};
lv_obj_t *game_key[4]{};
lv_obj_t *game_label=nullptr;
int64_t prior_tap=0;

void notice(const char *text) { if(message) lv_label_set_text(message,text); }
void action(const char *name,cJSON *args=nullptr){
    if(!strcmp(name,"music_control")){
        notice("Checking phone…");
        if(xTaskCreate([](void *parameter){
            auto *data=static_cast<cJSON *>(parameter);
            auto *result=execute("music_control",data);
            auto *failure=cJSON_GetObjectItem(result,"error");
            if(bsp_display_lock(100)==ESP_OK) {
                if(!lv_obj_has_flag(page,LV_OBJ_FLAG_HIDDEN))
                    notice(cJSON_IsString(failure)?failure->valuestring:"Phone command acknowledged");
                bsp_display_unlock();
            }
            cJSON_Delete(result);cJSON_Delete(data);vTaskDelete(nullptr);
        },"phone-command",4096,args,4,nullptr)!=pdPASS){
            cJSON_Delete(args);notice("Phone controls busy");
        }
        return;
    }
    auto *result=execute(name,args);
    auto *ok=cJSON_GetObjectItem(result,"ok"), *error=cJSON_GetObjectItem(result,"error");
    notice(cJSON_IsTrue(ok)?"Done":cJSON_IsString(error)?error->valuestring:"Unavailable");
    cJSON_Delete(result);cJSON_Delete(args);
}
cJSON *num(const char *key,double value){
    auto *out=cJSON_CreateObject();cJSON_AddNumberToObject(out,key,value);return out;
}
cJSON *word(const char *key,const char *value){
    auto *out=cJSON_CreateObject();cJSON_AddStringToObject(out,key,value);return out;
}
lv_obj_t *button(lv_obj_t *parent, const char *label,int x,int y,int w,int h,void (*cb)(lv_event_t *),void *data=nullptr){
    auto *btn=lv_button_create(parent);lv_obj_set_size(btn,w,h);
    lv_obj_align(btn,LV_ALIGN_CENTER,x,y);
    lv_obj_set_style_radius(btn,12,0);lv_obj_set_style_bg_color(btn,lv_color_hex(0x29505A),0);
    auto *text=lv_label_create(btn);lv_label_set_text(text,label);lv_obj_center(text);
    lv_obj_add_event_cb(btn,cb,LV_EVENT_CLICKED,data);return btn;
}
void clean_game(){game=0;game_label=nullptr;memset(game_key,0,sizeof game_key);}
void home(lv_event_t * =nullptr) {clean_game();lv_obj_add_flag(page,LV_OBJ_FLAG_HIDDEN);}
void screen(const char *title){
    clean_game();
    lv_obj_clean(page);lv_obj_remove_flag(page,LV_OBJ_FLAG_HIDDEN);
    auto *label=lv_label_create(page);lv_label_set_text(label,title);lv_obj_align(label,LV_ALIGN_TOP_MID,0,3);
    button(page,"Back",0,137,100,36,home);
    message=lv_label_create(page);lv_label_set_long_mode(message,LV_LABEL_LONG_WRAP);
    lv_obj_set_width(message,255);lv_obj_set_style_text_align(message,LV_TEXT_ALIGN_CENTER,0);
    lv_obj_align(message,LV_ALIGN_CENTER,0,105);
}
void preset(const char *name,const char *key,int arg){
    action(name,num(key,arg));
}
cJSON *mask_arguments(uint32_t mask){
    auto *args=cJSON_CreateObject();
    auto *ids=cJSON_AddArrayToObject(args,"ids");
    for(int i=0;i<24;++i)if(mask&(1u<<i))cJSON_AddItemToArray(ids,cJSON_CreateNumber(i));
    return args;
}
void catalog(lv_event_t * =nullptr){
    screen("Reaction library");
    uint32_t mask=settings.favorites;
    int id=catalog_at;
    if(category==3 && mask && !(mask&(1u<<id))){
        for(int i=0;i<24;++i)if(mask&(1u<<i)){catalog_at=i;break;}
        id=catalog_at;
    }
    auto *name=lv_label_create(page);
    lv_label_set_text_fmt(name,"%s\n%s",category==3?"Favorites":dizzy_face_style(id),
        category==3&&!mask?"Save a reaction first":dizzy_face_name(id));
    lv_obj_set_style_text_align(name,LV_TEXT_ALIGN_CENTER,0);lv_obj_align(name,LV_ALIGN_CENTER,0,-87);
    button(page,"Prev",-90,-36,80,37,[](lv_event_t*){
        int base=category<3?category*8:0;
        int length=category<3?8:24;
        for(int i=0;i<length;++i){
            catalog_at=base+(catalog_at-base+length-1)%length;
            if(category<3||!settings.favorites||settings.favorites&(1u<<catalog_at))break;
        }catalog();
    });
    button(page,"Preview",0,-36,90,37,[](lv_event_t*){
        show_reaction(catalog_at);home();
    });
    button(page,"Next",90,-36,80,37,[](lv_event_t*){
        int base=category<3?category*8:0;
        int length=category<3?8:24;
        for(int i=0;i<length;++i){
            catalog_at=base+(catalog_at-base+1)%length;
            if(category<3||!settings.favorites||settings.favorites&(1u<<catalog_at))break;
        }catalog();
    });
    button(page,(mask&(1u<<id))?"Unsave":"Favorite",-68,11,127,37,[](lv_event_t*){
        action("favorites_set",mask_arguments(settings.favorites^(1u<<catalog_at)));catalog();
    });
    button(page,"Style",69,11,126,37,[](lv_event_t*){
        category=(category+1)%4;catalog_at=category<3?category*8:0;catalog();
    });
    button(page,events[picked_event],-68,57,127,37,[](lv_event_t*){
        picked_event=(picked_event+1)%3;catalog();
    });
    button(page,"Assign saved",69,57,126,37,[](lv_event_t*){
        auto *args=mask_arguments(settings.favorites);
        cJSON_AddStringToObject(args,"event",event_keys[picked_event]);action("reaction_assign",args);
    });
}
void music(lv_event_t * =nullptr){
    screen("Phone music");
    auto *label=lv_label_create(page);
    lv_label_set_text(label,phone_discoverable?"Discoverable for 60 seconds":phone_connected?"Phone connected":"Phone disconnected");
    lv_obj_align(label,LV_ALIGN_CENTER,0,-99);
    button(page,"Pair",-80,-60,119,35,[](lv_event_t*){phone_command("PAIR",0,false);notice("Pair with Dizzy Music");});
    button(page,"Forget",80,-60,119,35,[](lv_event_t*){phone_command("FORGET",0,false);notice("Clearing phone pairings");});
    button(page,"Play / Pause",0,-12,145,39,[](lv_event_t*){action("music_control",word("command",phone_playing?"pause":"play"));});
    button(page,"Prev",-76,36,119,35,[](lv_event_t*){action("music_control",word("command","previous"));});
    button(page,"Next",76,36,119,35,[](lv_event_t*){action("music_control",word("command","next"));});
    auto *volume=lv_slider_create(page);lv_obj_set_width(volume,150);lv_obj_align(volume,LV_ALIGN_CENTER,0,76);
    lv_slider_set_value(volume,settings.volume,LV_ANIM_OFF);
    lv_obj_add_event_cb(volume,[](lv_event_t *e){
        action("volume_set",num("level",lv_slider_get_value(lv_event_get_target_obj(e))/100.0));
    },LV_EVENT_RELEASED,nullptr);
}
void motion_page(lv_event_t * =nullptr){
    screen("Movement");
    auto *label=lv_label_create(page);lv_label_set_text_fmt(label,"%s · %d BPM",armed?"Floor armed":"Floor disarmed",settings.tempo);
    lv_obj_align(label,LV_ALIGN_CENTER,0,-96);
    button(page,"Wave",-76,-58,122,35,[](lv_event_t*){action("motion_play",word("name","wave"));});
    button(page,"Tap tempo",76,-58,122,35,[](lv_event_t*){
        auto now=milliseconds(),interval=now-prior_tap;
        prior_tap=now;
        if(interval>=460&&interval<=1000){
            settings.tempo=std::clamp((int)(60000/interval),60,130);
            save_settings();motion_page();
        }else notice("Tap again on the beat");
    });
    constexpr const char *moves[]={"sway","heel","bounce","shuffle"};
    for(int i=0;i<4;++i)
        button(page,moves[i],i%2?76:-76,-14+45*(i/2),122,36,[](lv_event_t *e){
            action("motion_play",word("name",static_cast<const char *>(lv_event_get_user_data(e))));
        },const_cast<char *>(moves[i]));
    button(page,"Stop",0,73,110,36,[](lv_event_t*){action("motion_stop");});
}
void tools(lv_event_t * = nullptr){
    screen(tool_page?"Clock and alarms":"Desk tools");
    if(!tool_page){
        button(page,"25m focus",-75,-85,135,36,[](lv_event_t*){preset("focus_start","minutes",25);});
        button(page,"1m timer",75,-85,126,36,[](lv_event_t*){preset("timer_start","seconds",60);});
        button(page,"Stop timer",-75,-40,135,36,[](lv_event_t*){action("timer_cancel");});
        button(page,settings.quiet?"Unmute":"Quiet",75,-40,126,36,[](lv_event_t*){
            auto *a=cJSON_CreateObject();cJSON_AddBoolToObject(a,"enabled",!settings.quiet);
            action("quiet_set",a);tools();
        });
        button(page,watch_start?"Stop watch":"Start watch",-75,5,135,36,[](lv_event_t*){
            action("stopwatch",word("command",watch_start?"stop":"start"));tools();
        });
        button(page,"Reset watch",75,5,126,36,[](lv_event_t*){action("stopwatch",word("command","reset"));tools();});
        auto *elapsed=lv_label_create(page);
        lv_label_set_text_fmt(elapsed,"Stopwatch %.1f s",(watch_value+(watch_start?milliseconds()-watch_start:0))/1000.);
        lv_obj_align(elapsed,LV_ALIGN_CENTER,0,39);
    }else{
        button(page,"Alarm +5m",-75,-85,132,36,[](lv_event_t*){preset("alarm_add_minutes","minutes",5);});
        button(page,"Alarm +15m",75,-85,132,36,[](lv_event_t*){preset("alarm_add_minutes","minutes",15);});
        button(page,"Snooze",-75,-40,132,36,[](lv_event_t*){action("alarm_snooze");});
        button(page,"Dismiss",75,-40,132,36,[](lv_event_t*){action("alarm_dismiss");});
        button(page,"Clock style",-75,5,132,36,[](lv_event_t*){settings.clock_style=(settings.clock_style+1)%3;save_settings();notice("Clock style saved");});
        button(page,"Next alarm",75,5,132,36,[](lv_event_t*){
            time_t next=0;for(const auto &a:settings.alarms)if(a.at&&(!next||a.at<next))next=a.at;
            if(!next){notice("No upcoming alarm");return;}
            char text[45]{};tm tm{};localtime_r(&next,&tm);strftime(text,sizeof text,"Next %d %b at %H:%M",&tm);
            notice(text);
        });
    }
    button(page,tool_page?"Timers and focus":"Clock and alarms",0,72,175,35,[](lv_event_t*){tool_page^=1;tools();});
}
void finish_game(bool win,const char *text){
    if(win)react(Won);
    game=0;
    if(game_label)lv_label_set_text(game_label,text);
}
void run_game(int which){
    screen(which==1?"Reaction timing":which==2?"Memory sequence":"Rhythm taps");
    game=which;game_step=game_hits=game_round=0;cue_at=0;cue_used=true;game_started=milliseconds();
    game_label=lv_label_create(page);lv_obj_align(game_label,LV_ALIGN_CENTER,0,-43);
    lv_label_set_text(game_label,which==1?"Wait for Tap!":which==2?"Watch": "Tap at each light");
    if(game==2){
        for(int i=0;i<4;++i){
            sequence[i]=esp_random()%4;
            char label[4];snprintf(label,sizeof label,"%d",i+1);
            game_key[i]=button(page,label,(i%2)*96-48,4+42*(i/2),75,38,
                [](lv_event_t *e){
                    if(game!=2||milliseconds()-game_started<2500)return;
                    int id=(int)(intptr_t)lv_event_get_user_data(e);
                    if(id!=sequence[game_step++]) finish_game(false,"Try again");
                    else if(game_step==4)finish_game(true,"Sequence complete");
                },(void *)(intptr_t)i);
        }
    }else{
        game_key[0]=button(page,which==1?"Wait":"Tap",0,27,128,66,[](lv_event_t*){
            if(game==1){
                if(!cue_at)finish_game(false,"Too early");
                else{
                    char score[35];snprintf(score,sizeof score,"%lld ms",milliseconds()-cue_at);
                    finish_game(true,score);
                }
            }else if(game==3&&!cue_used&&milliseconds()-cue_at<310){
                cue_used=true;if(++game_hits==4)finish_game(true,"Four beats on time");
            }
        });
    }
}
void games(lv_event_t*){
    screen("Games");
    button(page,"Reaction timing",0,-69,190,43,[](lv_event_t*){run_game(1);});
    button(page,"Memory sequence",0,-9,190,43,[](lv_event_t*){run_game(2);});
    button(page,"Rhythm taps",0,51,190,43,[](lv_event_t*){run_game(3);});
}
void menu(lv_event_t*){
    screen("Dizzy");
    button(page,"Reactions",-76,-66,134,42,catalog);
    button(page,"Movement",76,-66,134,42,motion_page);
    button(page,"Phone music",-76,-11,134,42,music);
    button(page,"Desk tools",76,-11,134,42,tools);
    button(page,"Games",-76,44,134,42,games);
    button(page,"Send wave",76,44,134,42,[](lv_event_t*){request_gesture("wave");notice("Sending wave");});
}
void tick(lv_timer_t *) {
    auto t=milliseconds();
    int phase=(int)((t-reaction_started)%60000);
    int id=t-reaction_started<2600?reaction.load():DIZZY_FACE_IDLE;
    const char *mode="";
    switch(voice){
        case Recording:id=DIZZY_FACE_RECORDING; mode="Recording"; break;
        case Thinking:id=DIZZY_FACE_THINKING;mode="Thinking";break;
        case Speaking:id=DIZZY_FACE_SPEAKING;mode="Speaking";break;
        case VoiceFault:id=DIZZY_FACE_FAULT;mode="Voice unavailable";break;
    }
    if(motor_fault&&voice==Ready){id=DIZZY_FACE_FAULT;mode="Motion locked";}
    if(ringing){id=DIZZY_FACE_ALARM;mode="Alarm · tap crown to snooze";}
    if(lv_obj_has_flag(page,LV_OBJ_FLAG_HIDDEN))face.update(id,phase);
    lv_label_set_text(mode_label,mode);
    static time_t shown=0;
    time_t now=time(nullptr);
    if(now!=shown){
        shown=now;char text[45]="Set clock with Mac bridge";
        if(now>1700000000){
            tm tm{};localtime_r(&now,&tm);
            strftime(text,sizeof text,settings.clock_style==1?"%I:%M %p":settings.clock_style==2?"%a %d %b · %H:%M":"%H:%M",&tm);
        }
        lv_label_set_text(clock_label,text);
        lv_obj_align(clock_label,LV_ALIGN_CENTER,(int)(now%9)-4,-133+(int)((now/7)%7)-3);
    }
    if(!game)return;
    auto elapsed=t-game_started;
    if(game==1&&elapsed>=1400&&!cue_at){
        cue_at=t;lv_label_set_text(lv_obj_get_child(game_key[0],0),"Tap!");
    }else if(game==2){
        int active=elapsed<300||elapsed>=2500?-1:(elapsed-300)/550;
        for(int i=0;i<4;++i)lv_obj_set_style_bg_color(game_key[i],lv_color_hex(
            active>=0&&active<4&&sequence[active]==i&&elapsed%550<330?0x58AA91:0x29505A),0);
        if(elapsed>=2500)lv_label_set_text_static(game_label,"Repeat");
    }else if(game==3&&elapsed>=600*(game_round+1)){
        if(++game_round>8)finish_game(false,"Try again");
        else{cue_at=t;cue_used=false;}
    }
    if(game==3)lv_obj_set_style_bg_color(game_key[0],lv_color_hex(t-cue_at<230&&!cue_used?0x58AA91:0x29505A),0);
}
}

void setup_interface(){
    if(!bsp_display_start())return;
    bsp_display_brightness_set(60);
    if(bsp_display_lock(500)!=ESP_OK)return;
    auto *root=lv_screen_active();
    lv_obj_set_style_bg_color(root,lv_color_hex(0x050B11),0);
    face.create(root);
    clock_label=lv_label_create(root);lv_obj_set_style_text_color(clock_label,lv_color_hex(0x9FDDD1),0);
    mode_label=lv_label_create(root);lv_obj_set_style_text_color(mode_label,lv_color_hex(0xB1E0D2),0);
    lv_obj_align(mode_label,LV_ALIGN_CENTER,0,101);
    button(root,"Menu",-54,145,96,43,menu);
    button(root,"Pet",54,145,96,43,[](lv_event_t*){react(Petted);});
    page=lv_obj_create(root);lv_obj_center(page);lv_obj_set_size(page,310,330);
    lv_obj_set_style_bg_color(page,lv_color_hex(0x13252E),0);
    lv_obj_set_style_border_width(page,0,0);lv_obj_set_style_text_color(page,lv_color_hex(0xD6ECE7),0);
    lv_obj_remove_flag(page,LV_OBJ_FLAG_SCROLLABLE);lv_obj_add_flag(page,LV_OBJ_FLAG_HIDDEN);
    lv_timer_create(tick,33,nullptr);
    bsp_display_unlock();
}
