#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstring>
#include "driver/i2s_std.h"
#include "driver/uart.h"
#include "esp_a2dp_api.h"
#include "esp_avrc_api.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_bt_api.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"
#include "freertos/task.h"
#include "nvs_flash.h"

namespace {
constexpr auto control_uart = UART_NUM_2;
i2s_chan_handle_t speaker = nullptr;
StreamBufferHandle_t pcm;
std::atomic<int> gain{50}, sample_rate{44100}, channel_count{2};
std::atomic<bool> connected{false}, playing{false}, avrc{false}, discoverable{false};
esp_bd_addr_t peer{};
int64_t pair_until=0;
uint8_t transaction=0;

void send(const char *line) { uart_write_bytes(control_uart,line,strlen(line)); }
void state() {
    char line[48];
    snprintf(line,sizeof line,"STATE %d %d %d\n",connected.load(),playing.load(),discoverable.load());
    send(line);
}

void pairing(bool active) {
    discoverable=active;
    esp_bt_gap_set_scan_mode(ESP_BT_CONNECTABLE,active?ESP_BT_GENERAL_DISCOVERABLE:ESP_BT_NON_DISCOVERABLE);
    if (active) pair_until=esp_timer_get_time()+60*1000*1000;
    state();
}

void gap(esp_bt_gap_cb_event_t event,esp_bt_gap_cb_param_t *p) {
    if(event==ESP_BT_GAP_CFM_REQ_EVT)
        esp_bt_gap_ssp_confirm_reply(p->cfm_req.bda,discoverable.load() || connected.load());
    if(event==ESP_BT_GAP_PIN_REQ_EVT) {
        esp_bt_pin_code_t pin={'0','0','0','0'};
        esp_bt_gap_pin_reply(p->pin_req.bda,discoverable.load() && !p->pin_req.min_16_digit,4,pin);
    }
}

void a2dp(esp_a2d_cb_event_t event,esp_a2d_cb_param_t *p) {
    if(event==ESP_A2D_CONNECTION_STATE_EVT) {
        if(p->conn_stat.state==ESP_A2D_CONNECTION_STATE_CONNECTED) {
            memcpy(peer,p->conn_stat.remote_bda,sizeof peer);
            connected=true;
            pairing(false);
        } else if(p->conn_stat.state==ESP_A2D_CONNECTION_STATE_DISCONNECTED) {
            connected=false; playing=false; avrc=false; state();
        }
    } else if(event==ESP_A2D_AUDIO_STATE_EVT) {
        playing=p->audio_stat.state==ESP_A2D_AUDIO_STATE_STARTED;
        state();
    } else if(event==ESP_A2D_AUDIO_CFG_EVT && p->audio_cfg.mcc.type==ESP_A2D_MCT_SBC) {
        const auto &info=p->audio_cfg.mcc.cie.sbc_info;
        sample_rate=info.samp_freq & ESP_A2D_SBC_CIE_SF_48K?48000:
            info.samp_freq & ESP_A2D_SBC_CIE_SF_44K?44100:
            info.samp_freq & ESP_A2D_SBC_CIE_SF_32K?32000:16000;
        channel_count=(info.ch_mode & ESP_A2D_SBC_CIE_CH_MODE_MONO)?1:2;
    }
}

void receive_pcm(const uint8_t *data,uint32_t length) {
    // Drop whole blocks if playback is behind so the PCM framing stays aligned.
    if (xStreamBufferSpacesAvailable(pcm)>=length) xStreamBufferSend(pcm,data,length,0);
}

void avrc_events(esp_avrc_ct_cb_event_t evt,esp_avrc_ct_cb_param_t *p) {
    if(evt==ESP_AVRC_CT_CONNECTION_STATE_EVT) avrc=p->conn_stat.connected;
}

void audio_out(void *) {
    i2s_chan_config_t channel=I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0,I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&channel,&speaker,nullptr));
    i2s_std_config_t cfg{};
    cfg.clk_cfg=I2S_STD_CLK_DEFAULT_CONFIG(44100);
    cfg.slot_cfg=I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,I2S_SLOT_MODE_STEREO);
    cfg.gpio_cfg={.mclk=I2S_GPIO_UNUSED,.bclk=GPIO_NUM_26,.ws=GPIO_NUM_25,
        .dout=GPIO_NUM_22,.din=I2S_GPIO_UNUSED,.invert_flags={}};
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(speaker,&cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(speaker));
    int actual=44100, smooth=0;
    int16_t input[512], output[1024];
    while(true) {
        auto bytes=xStreamBufferReceive(pcm,input,sizeof input,pdMS_TO_TICKS(30));
        if(!bytes || !playing) continue;
        if(actual!=sample_rate.load()) {
            actual=sample_rate;
            i2s_std_clk_config_t clock=I2S_STD_CLK_DEFAULT_CONFIG((uint32_t)actual);
            i2s_channel_disable(speaker);
            i2s_channel_reconfig_std_clock(speaker,&clock);
            i2s_channel_enable(speaker);
        }
        const int channels=channel_count;
        size_t samples=bytes/(sizeof(int16_t)*channels);
        int target=gain.load()*256;
        for(size_t i=0;i<samples;++i) {
            smooth+=std::clamp(target-smooth,-48,48);
            int mono=input[i*channels];
            if(channels==2) mono=(mono+input[i*2+1])/2;
            output[i*2]=output[i*2+1]=(int16_t)(mono*smooth/25600);
        }
        size_t written;
        i2s_channel_write(speaker,output,samples*4,&written,30);
    }
}

const char *media(uint8_t opcode) {
    if (!connected) return "DISCONNECTED";
    if (!avrc) return "UNSUPPORTED";
    bool ok=esp_avrc_ct_send_passthrough_cmd(transaction++ & 15,opcode,ESP_AVRC_PT_CMD_STATE_PRESSED)==ESP_OK;
    ok=(esp_avrc_ct_send_passthrough_cmd(transaction++ & 15,opcode,ESP_AVRC_PT_CMD_STATE_RELEASED)==ESP_OK) && ok;
    if (!ok) return "UNSUPPORTED";
    if (opcode==ESP_AVRC_PT_CMD_PLAY || opcode==ESP_AVRC_PT_CMD_PAUSE) {
        auto expected=opcode==ESP_AVRC_PT_CMD_PLAY;
        for (int attempt=0; attempt<12 && playing.load()!=expected; ++attempt)
            vTaskDelay(pdMS_TO_TICKS(100));
        return playing.load()==expected?"OK":"UNCONFIRMED";
    }
    return "QUEUED";
}

void command(char *line) {
    int id=0, value=0;
    char op[20]{};
    if (sscanf(line,"%d %19s %d",&id,op,&value)<2) return;
    const char *result="OK";
    if(!strcmp(op,"PAIR")) pairing(true);
    else if(!strcmp(op,"GAIN")) gain=std::clamp(value,0,100);
    else if(!strcmp(op,"FORGET")) {
        pairing(false);
        if(connected) esp_a2d_sink_disconnect(peer);
        int count=esp_bt_gap_get_bond_device_num();
        if(count>0) {
            auto *list=new esp_bd_addr_t[count];
            if(esp_bt_gap_get_bond_device_list(&count,list)==ESP_OK)
                for(int i=0;i<count;++i) esp_bt_gap_remove_bond_device(list[i]);
            delete[] list;
        }
    } else if(!strcmp(op,"PLAY")) result=media(ESP_AVRC_PT_CMD_PLAY);
    else if(!strcmp(op,"PAUSE")) result=media(ESP_AVRC_PT_CMD_PAUSE);
    else if(!strcmp(op,"NEXT")) result=media(ESP_AVRC_PT_CMD_FORWARD);
    else if(!strcmp(op,"PREVIOUS")) result=media(ESP_AVRC_PT_CMD_BACKWARD);
    else result="UNKNOWN";
    if(id) {
        char response[52];
        snprintf(response,sizeof response,"ACK %d %s\n",id,result);
        send(response);
    }
    state();
}
}

extern "C" void app_main() {
    auto status=nvs_flash_init();
    if(status==ESP_ERR_NVS_NO_FREE_PAGES || status==ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase()); status=nvs_flash_init();
    }
    ESP_ERROR_CHECK(status);
    const uart_config_t cfg={.baud_rate=115200,.data_bits=UART_DATA_8_BITS,.parity=UART_PARITY_DISABLE,
        .stop_bits=UART_STOP_BITS_1,.flow_ctrl=UART_HW_FLOWCTRL_DISABLE,.source_clk=UART_SCLK_DEFAULT};
    ESP_ERROR_CHECK(uart_param_config(control_uart,&cfg));
    ESP_ERROR_CHECK(uart_set_pin(control_uart,17,16,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(control_uart,1024,0,0,nullptr,0));
    pcm=xStreamBufferCreate(16384,512);
    xTaskCreate(audio_out,"i2s-audio",4096,nullptr,7,nullptr);
    esp_bt_controller_config_t controller=BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bt_controller_init(&controller));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_CLASSIC_BT));
    ESP_ERROR_CHECK(esp_bluedroid_init());
    ESP_ERROR_CHECK(esp_bluedroid_enable());
    ESP_ERROR_CHECK(esp_bt_gap_register_callback(gap));
    ESP_ERROR_CHECK(esp_bt_gap_set_device_name("Dizzy Music"));
    ESP_ERROR_CHECK(esp_avrc_ct_init());
    ESP_ERROR_CHECK(esp_avrc_ct_register_callback(avrc_events));
    ESP_ERROR_CHECK(esp_a2d_register_callback(a2dp));
    ESP_ERROR_CHECK(esp_a2d_sink_init());
    ESP_ERROR_CHECK(esp_a2d_sink_register_data_callback(receive_pcm));
    pairing(false);
    char line[80]{}; size_t used=0;
    int64_t last_state=0;
    while (true) {
        char ch=0;
        if(uart_read_bytes(control_uart,&ch,1,pdMS_TO_TICKS(50))==1) {
            if(ch=='\n') {line[used]=0;command(line);used=0;}
            else if(ch!='\r' && used<sizeof line-1) line[used++]=ch;
        }
        auto now=esp_timer_get_time();
        if(discoverable && now>=pair_until) pairing(false);
        if(now-last_state>1'000'000) {state();last_state=now;}
    }
}
