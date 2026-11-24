#pragma once
#include "face.h"
#include "lvgl.h"
#include <algorithm>
#include <cmath>

inline void dizzy_face_draw(lv_layer_t *layer, int x, int y, int face, int phase) {
    DizzyShape shapes[64];
    int count = dizzy_face(face, phase, shapes, 64);
    for (int index=0; index<count; ++index) {
        const auto &s = shapes[index];
        lv_color_t color = lv_color_hex(s.color);
        if (s.kind == DIZZY_LINE) {
            lv_draw_line_dsc_t dsc;
            lv_draw_line_dsc_init(&dsc);
            dsc.p1 = {(lv_value_precise_t)(x+s.x),(lv_value_precise_t)(y+s.y)};
            dsc.p2 = {(lv_value_precise_t)(x+s.a),(lv_value_precise_t)(y+s.b)};
            dsc.color=color; dsc.width=s.radius; dsc.round_start=dsc.round_end=1;
            lv_draw_line(layer,&dsc);
            continue;
        }
        lv_draw_rect_dsc_t dsc;
        lv_draw_rect_dsc_init(&dsc);
        dsc.bg_color=color; dsc.bg_opa=LV_OPA_COVER;
        if (s.kind == DIZZY_RECT || s.a == s.b) {
            int left = x+s.x, top = y+s.y;
            if (s.kind == DIZZY_ELLIPSE) {
                left-=s.a/2; top-=s.b/2; dsc.radius=LV_RADIUS_CIRCLE;
            } else dsc.radius=s.radius;
            lv_area_t a{left,top,left+s.a-1,top+s.b-1};
            lv_draw_rect(layer,&dsc,&a);
        } else {
            int top=y+s.y-s.b/2;
            int step=s.b>32?3:2;
            for (int row=0; row<s.b; row+=step) {
                double dy=(row+0.5)*2/s.b-1;
                int half=std::max(1,(int)std::round(s.a/2*std::sqrt(std::max(0.0,1-dy*dy))));
                lv_area_t a{x+s.x-half,top+row,x+s.x+half,top+std::min<int>(row+step,s.b)-1};
                lv_draw_rect(layer,&dsc,&a);
            }
        }
    }
}

struct DizzyFaceView {
    lv_obj_t *surface=nullptr;
    int face=DIZZY_FACE_IDLE;
    int phase=0;
    void create(lv_obj_t *screen) {
        surface=lv_obj_create(screen);
        lv_obj_remove_style_all(surface);
        lv_obj_set_size(surface,466,466);
        lv_obj_center(surface);
        lv_obj_remove_flag(surface,LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_remove_flag(surface,LV_OBJ_FLAG_CLICKABLE);
        lv_obj_add_event_cb(surface,[](lv_event_t *event) {
            auto *view=(DizzyFaceView *)lv_event_get_user_data(event);
            lv_area_t area;
            lv_obj_get_coords(view->surface,&area);
            dizzy_face_draw(lv_event_get_layer(event),area.x1,area.y1,view->face,view->phase);
        },LV_EVENT_DRAW_MAIN,this);
    }
    void update(int id, int ms) {
        if (id==face && (ms==phase ||
            (id==DIZZY_FACE_IDLE && ((phase%5300>=5160)==(ms%5300>=5160))))) {
            phase=ms;
            return;
        }
        face=id; phase=ms;
        lv_obj_invalidate(surface);
    }
};
