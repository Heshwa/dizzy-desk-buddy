#include "device.hpp"
#include "bsp/esp32_s3_touch_amoled_1_75.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <sys/time.h>
#include "esp_event.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

namespace {
const std::string base=CONFIG_DIZZY_BRIDGE;
std::atomic<bool> net{false};
QueueHandle_t gestures=nullptr;
SemaphoreHandle_t codec_lock=nullptr;
esp_codec_dev_handle_t speaker=nullptr, mic=nullptr;
constexpr const char *physical_id="dizzy-v2-hardware";

struct HttpReply {int code=0;std::string data;};
esp_err_t capture_http(esp_http_client_event_t *ev) {
    auto *box=static_cast<HttpReply *>(ev->user_data);
    if(ev->event_id==HTTP_EVENT_ON_DATA){
        if(box->data.size()+ev->data_len>1'000'000) return ESP_ERR_NO_MEM;
        box->data.append(static_cast<const char *>(ev->data),ev->data_len);
    }
    return ESP_OK;
}
HttpReply http(const char *path, const char *data=nullptr,size_t bytes=0,
        const char *type="application/json",int timeout=2500) {
    HttpReply reply;
    if(base.empty()||!net||!CONFIG_DIZZY_DEVICE_TOKEN[0])return reply;
    std::string url=base+path;
    esp_http_client_config_t cfg{};
    cfg.url=url.c_str();cfg.timeout_ms=timeout;cfg.event_handler=capture_http;cfg.user_data=&reply;
    cfg.method=data?HTTP_METHOD_POST:HTTP_METHOD_GET;
    cfg.disable_auto_redirect=true;
    auto client=esp_http_client_init(&cfg);
    if(!client)return reply;
    const std::string authorization="Bearer " CONFIG_DIZZY_DEVICE_TOKEN;
    esp_http_client_set_header(client,"Authorization",authorization.c_str());
    if(data){esp_http_client_set_header(client,"Content-Type",type);esp_http_client_set_post_field(client,data,bytes);}
    if(esp_http_client_perform(client)==ESP_OK)reply.code=esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
    return reply;
}
HttpReply send_json(const char *path,cJSON *doc){
    char *data=cJSON_PrintUnformatted(doc);
    HttpReply reply;
    if(data){reply=http(path,data,strlen(data));cJSON_free(data);}
    cJSON_Delete(doc);
    return reply;
}
void network_event(void *,esp_event_base_t base_id,int32_t id,void *){
    if(base_id==WIFI_EVENT&&id==WIFI_EVENT_STA_START)esp_wifi_connect();
    if(base_id==WIFI_EVENT&&id==WIFI_EVENT_STA_DISCONNECTED){net=false;esp_wifi_connect();}
    if(base_id==IP_EVENT&&id==IP_EVENT_STA_GOT_IP)net=true;
}
void show_error(const char *message){
    snprintf(status_text,sizeof status_text,"%s",message);
    voice=VoiceFault;
}
void update_clock(const cJSON *epoch) {
    static int64_t last_sync=0;
    if(!cJSON_IsNumber(epoch)||epoch->valuedouble<1700000000||epoch->valuedouble>4102444800)return;
    if(milliseconds()-last_sync<300000 && time(nullptr)>1700000000 && last_sync)return;
    time_t now=(time_t)epoch->valuedouble;
    if(llabs(now-time(nullptr))>=2){
        timeval value{now,0};settimeofday(&value,nullptr);
        board_rtc_set(now);
    }
    last_sync=milliseconds();
}
void bridge_task(void *) {
    int64_t last_report=0;
    char gesture;
    while(true){
        auto reply=http("/api/device/next",nullptr,0,"application/json",800);
        bridge_online=reply.code==200;
        if(bridge_online){
            auto *command=cJSON_Parse(reply.data.c_str());
            if(command){
                update_clock(cJSON_GetObjectItem(command,"epoch"));
                auto *id=cJSON_GetObjectItem(command,"id"),*name=cJSON_GetObjectItem(command,"action");
                if(cJSON_IsString(id)&&cJSON_IsString(name)){
                    auto *report=cJSON_CreateObject();
                    cJSON_AddStringToObject(report,"id",id->valuestring);
                    cJSON_AddItemToObject(report,"response",execute(name->valuestring,cJSON_GetObjectItem(command,"args")));
                    cJSON_AddItemToObject(report,"state",snapshot());
                    send_json("/api/device/result",report);
                    last_report=milliseconds();
                }
                cJSON_Delete(command);
            }
            if(milliseconds()-last_report>=1000) {
                auto *report=cJSON_CreateObject();cJSON_AddItemToObject(report,"state",snapshot());
                send_json("/api/device/result",report);last_report=milliseconds();
            }
        }
        if(gestures&&xQueueReceive(gestures,&gesture,0)){
            if(bridge_online){
                auto *req=cJSON_CreateObject();cJSON_AddStringToObject(req,"gesture",gesture=='g'?"goodnight":"wave");
                auto posted=send_json("/api/device/gesture",req);
                auto *response=cJSON_Parse(posted.data.c_str());
                if(cJSON_IsTrue(cJSON_GetObjectItem(response,"ok")))react(Greeted);
                else snprintf(status_text,sizeof status_text,"Partner unavailable");
                cJSON_Delete(response);
            }else snprintf(status_text,sizeof status_text,"Partner bridge offline");
        }
        vTaskDelay(pdMS_TO_TICKS(bridge_online?110:400));
    }
}
uint16_t word(const char *p){return (uint8_t)p[0]|((uint8_t)p[1]<<8);}
uint32_t dword(const char *p){return word(p)|((uint32_t)word(p+2)<<16);}
bool play_wav(const std::string &wav){
    if(!speaker||wav.size()<44||wav.compare(0,4,"RIFF")||wav.compare(8,4,"WAVE"))return false;
    int sample_rate=0;
    for(size_t offset=12;offset+8<=wav.size();){
        const char *tag=wav.data()+offset;
        size_t bytes=dword(tag+4);
        offset+=8;
        if(bytes>wav.size()-offset)return false;
        if(!memcmp(tag,"fmt ",4)&&bytes>=16){
            auto *format=wav.data()+offset;
            if(word(format)!=1||word(format+2)!=1||word(format+14)!=16)return false;
            sample_rate=dword(format+4);
        }else if(!memcmp(tag,"data",4)&&sample_rate>=8000&&sample_rate<=48000){
            esp_codec_dev_sample_info_t format{};
            format.sample_rate=sample_rate;format.channel=1;format.bits_per_sample=16;
            if(esp_codec_dev_open(speaker,&format)!=ESP_CODEC_DEV_OK)return false;
            esp_codec_dev_set_out_vol(speaker,settings.volume);
            for(size_t at=0;at<bytes;at+=2048){
                if(ringing)break;
                // Codec write accepts mutable buffers. Copy one DMA-sized block.
                uint8_t samples[2048];
                auto span=std::min<size_t>(sizeof samples,bytes-at);
                memcpy(samples,wav.data()+offset+at,span);
                if(esp_codec_dev_write(speaker,samples,span)!=ESP_CODEC_DEV_OK){esp_codec_dev_close(speaker);return false;}
            }
            esp_codec_dev_close(speaker);return true;
        }
        offset+=bytes+(bytes&1);
    }
    return false;
}
void audio_task(void *) {
    constexpr size_t max_samples=480000;
    auto *samples=(int16_t *)heap_caps_malloc(max_samples*sizeof(int16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    while(true){
        if(!record_requested){vTaskDelay(pdMS_TO_TICKS(25));continue;}
        if(!mic||!samples||ringing){record_requested=false;show_error("Microphone unavailable");continue;}
        if(xSemaphoreTake(codec_lock,pdMS_TO_TICKS(500))!=pdTRUE){
            record_requested=false;show_error("Audio is busy");continue;
        }
        esp_codec_dev_sample_info_t format{};
        format.sample_rate=16000;format.channel=2;format.bits_per_sample=16;
        format.channel_mask=ESP_CODEC_DEV_MAKE_CHANNEL_MASK(0)|ESP_CODEC_DEV_MAKE_CHANNEL_MASK(1);
        if(esp_codec_dev_open(mic,&format)!=ESP_CODEC_DEV_OK){
            xSemaphoreGive(codec_lock);record_requested=false;show_error("Could not open microphone");continue;
        }
        esp_codec_dev_set_in_gain(mic,30);
        size_t used=0;
        int16_t block[640]{};
        int64_t cutoff=milliseconds()+30000;
        while(record_requested&&used+320<=max_samples&&milliseconds()<cutoff){
            if(esp_codec_dev_read(mic,block,sizeof block)!=ESP_CODEC_DEV_OK)break;
            for(int i=0;i<320;++i)samples[used++]=block[2*i];
        }
        esp_codec_dev_close(mic);xSemaphoreGive(codec_lock);
        record_requested=false;voice=Thinking;
        if(used<1600){show_error("Record a short phrase");continue;}
        auto output=http("/api/speech?device=dizzy-v2-hardware",reinterpret_cast<const char *>(samples),
            used*sizeof(*samples),"application/octet-stream",60000);
        auto *document=cJSON_Parse(output.data.c_str());
        auto *audio=cJSON_GetObjectItem(document,"audio");
        auto *error=cJSON_GetObjectItem(document,"error");
        if(!cJSON_IsString(audio)||strncmp(audio->valuestring,"/api/audio/",11)){
            show_error(cJSON_IsString(error)?error->valuestring:"Voice service unavailable");cJSON_Delete(document);continue;
        }
        auto wav=http(audio->valuestring,nullptr,0,"audio/wav",10000);
        cJSON_Delete(document);
        if(wav.code!=200||xSemaphoreTake(codec_lock,pdMS_TO_TICKS(1500))!=pdTRUE){show_error("Reply audio unavailable");continue;}
        voice=Speaking;
        bool ok=play_wav(wav.data);
        xSemaphoreGive(codec_lock);
        if(ok)voice=Ready;else show_error("Could not play reply");
    }
}

void alarm_task(void *){
    int64_t last_sound=0;
    while(true){
        auto now=milliseconds();
        if(ringing && !settings.quiet && speaker && now-last_sound>=1100 && xSemaphoreTake(codec_lock,0)==pdTRUE){
            last_sound=now;
            esp_codec_dev_sample_info_t format{};
            format.sample_rate=16000;format.channel=1;format.bits_per_sample=16;
            if(esp_codec_dev_open(speaker,&format)==ESP_CODEC_DEV_OK){
                esp_codec_dev_set_out_vol(speaker,settings.volume);
                int16_t tone[320];
                for(int frame=0;frame<14&&ringing;++frame){
                    for(int i=0;i<320;++i) tone[i]=frame>=6&&frame<8?0:
                        (int16_t)(2000*std::sin((i+320*frame)*(frame<6?.29:.37)));
                    esp_codec_dev_write(speaker,tone,sizeof tone);
                }
                esp_codec_dev_close(speaker);
            }
            xSemaphoreGive(codec_lock);
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
}

void request_gesture(const char *gesture){
    if(gestures) {
        char code=!strcmp(gesture,"goodnight")?'g':'w';
        xQueueSend(gestures,&code,0);
    }
}

void setup_network(){
    gestures=xQueueCreate(4,sizeof(char));
    codec_lock=xSemaphoreCreateMutex();
    speaker=bsp_audio_codec_speaker_init();
    mic=bsp_audio_codec_microphone_init();
    xTaskCreate(audio_task,"mic-voice",9216,nullptr,4,nullptr);
    xTaskCreate(alarm_task,"local-alarm",4096,nullptr,5,nullptr);
    if(!CONFIG_DIZZY_WIFI_SSID[0] || base.empty() || !CONFIG_DIZZY_DEVICE_TOKEN[0])return;
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,network_event,nullptr);
    esp_event_handler_register(IP_EVENT,IP_EVENT_STA_GOT_IP,network_event,nullptr);
    wifi_config_t cfg{};
    strlcpy(reinterpret_cast<char *>(cfg.sta.ssid),CONFIG_DIZZY_WIFI_SSID,sizeof cfg.sta.ssid);
    strlcpy(reinterpret_cast<char *>(cfg.sta.password),CONFIG_DIZZY_WIFI_PASSWORD,sizeof cfg.sta.password);
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
    xTaskCreate(bridge_task,"mac-bridge",8192,nullptr,4,nullptr);
}
