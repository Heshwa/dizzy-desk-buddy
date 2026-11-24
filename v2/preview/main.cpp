#include "face_lvgl.hpp"
#include <SDL.h>
#include <cstdio>
#include <string_view>

static void flush(lv_display_t *display,const lv_area_t *area,uint8_t *pixels) {
    auto *texture=static_cast<SDL_Texture *>(lv_display_get_user_data(display));
    SDL_Rect region{area->x1,area->y1,lv_area_get_width(area),lv_area_get_height(area)};
    SDL_UpdateTexture(texture,&region,pixels,region.w*4);
    lv_display_flush_ready(display);
}

int main(int argc,char **argv) {
    if (SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER)!=0) return 1;
    bool test=argc>1 && std::string_view(argv[1])=="--test";
    auto *window=SDL_CreateWindow("Dizzy V2 AMOLED Preview",SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,466,466,test?SDL_WINDOW_HIDDEN:0);
    auto *renderer=window?SDL_CreateRenderer(window,-1,SDL_RENDERER_SOFTWARE):nullptr;
    auto *texture=renderer?SDL_CreateTexture(renderer,SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_STREAMING,466,466):nullptr;
    if (!texture) {std::fprintf(stderr,"%s\n",SDL_GetError());return 1;}
    lv_init(); lv_tick_set_cb(SDL_GetTicks);
    auto *display=lv_display_create(466,466);
    static uint32_t buffer[466*80];
    lv_display_set_buffers(display,buffer,nullptr,sizeof(buffer),LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_user_data(display,texture);
    lv_display_set_flush_cb(display,flush);
    auto *screen=lv_screen_active();
    lv_obj_set_style_bg_color(screen,lv_color_hex(0x050b11),0);
    DizzyFaceView face; face.create(screen);
    auto *name=lv_label_create(screen);
    lv_obj_set_style_text_color(name,lv_color_hex(0xb9ded9),0);
    lv_obj_align(name,LV_ALIGN_CENTER,0,115);
    bool running=true; int index=24; auto start=SDL_GetTicks(); unsigned frames=0;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type==SDL_QUIT || (event.type==SDL_KEYDOWN && event.key.keysym.sym==SDLK_ESCAPE)) running=false;
            if (event.type==SDL_KEYDOWN || event.type==SDL_MOUSEBUTTONDOWN) {
                const bool previous=event.type==SDL_KEYDOWN && event.key.keysym.sym==SDLK_LEFT;
                index=(index+(previous?29:1))%30; start=SDL_GetTicks();
            }
        }
        if(test) index=(int)frames%30;
        lv_label_set_text_static(name,dizzy_face_name(index));
        face.update(index,(int)(SDL_GetTicks()-start));
        lv_timer_handler();
        SDL_RenderCopy(renderer,texture,nullptr,nullptr);
        SDL_RenderPresent(renderer);
        if(test && ++frames>=30) running=false;
        SDL_Delay(test?35:33);
    }
    SDL_DestroyTexture(texture); SDL_DestroyRenderer(renderer); SDL_DestroyWindow(window); SDL_Quit();
    if(test) std::puts("Rendered 24 reactions and 6 status faces with LVGL.");
}
