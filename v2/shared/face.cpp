#include "face.h"
#include <algorithm>
#include <cmath>

namespace {
constexpr const char *names[] = {
    "Soft smile", "Big grin", "Curious tilt", "Playful wink", "Starry eyes", "Head in clouds",
    "Found you", "Warm hug", "Pixel smile", "High score", "Thinking squares", "Pixel wink",
    "Power up", "Sleep mode", "Surprise!", "Pixel heart", "Moonbeam", "Sunburst",
    "Little detective", "Side-eye", "Twinkle", "Dream time", "Wide awake", "Heart orbit",
    "Idle", "Recording", "Thinking", "Speaking", "Alarm", "Fault"
};
constexpr uint32_t palettes[][4] = {
    {0x7DEED4, 0x254B55, 0xF98576, 0x0A2228},
    {0xB6F17C, 0x2B502F, 0xF6B67D, 0x18271E},
    {0xB8A8FF, 0x433867, 0xFF8ABA, 0x201839}
};
struct Painter {
    DizzyShape *out;
    int capacity;
    int size = 0;
    void put(int kind, int x, int y, int a, int b, int round, uint32_t color) {
        if (size < capacity) out[size++] = {(int16_t)kind,(int16_t)x,(int16_t)y,
            (int16_t)a,(int16_t)b,(int16_t)round,color};
    }
    void ellipse(int x,int y,int w,int h,uint32_t c) { put(DIZZY_ELLIPSE,x,y,w,h,0,c); }
    void rect(int x,int y,int w,int h,int r,uint32_t c) { put(DIZZY_RECT,x,y,w,h,r,c); }
    void line(int x,int y,int x1,int y1,int w,uint32_t c) { put(DIZZY_LINE,x,y,x1,y1,w,c); }
    void star(int x,int y,int r,uint32_t c) {
        line(x-r,y,x+r,y,4,c); line(x,y-r,x,y+r,4,c);
        line(x-r/2,y-r/2,x+r/2,y+r/2,3,c);
        line(x-r/2,y+r/2,x+r/2,y-r/2,3,c);
    }
    void heart(int x,int y,uint32_t c) {
        ellipse(x-12,y-8,28,27,c); ellipse(x+12,y-8,28,27,c);
        line(x-16,y-2,x,y+16,18,c); line(x+16,y-2,x,y+16,18,c);
    }
};
}

const char *dizzy_face_name(int id) {
    return id >= 0 && id <= DIZZY_FACE_FAULT ? names[id] : "";
}
const char *dizzy_face_style(int id) {
    return id < 0 || id >= DIZZY_FACE_COUNT ? "Status" :
        id < 8 ? "Mint" : id < 16 ? "Pixel" : "Starlight";
}

int dizzy_face(int id, int ms, DizzyShape *out, int capacity) {
    if (!out || capacity <= 0) return 0;
    if (id < 0 || id > DIZZY_FACE_FAULT) id = DIZZY_FACE_IDLE;
    int style = id < 24 ? id / 8 : 0;
    int mood = id < 24 ? id % 8 : -1;
    const auto &palette = palettes[style];
    uint32_t bright = palette[0], shade = palette[1], accent = palette[2], halo = palette[3];
    if (id == DIZZY_FACE_ALARM || id == DIZZY_FACE_FAULT) bright = 0xFFA06E;
    Painter p{out, capacity};
    const int pulse = (int)std::round(std::sin(ms * 0.009) * 5);
    const bool introduction = ms < 220;
    const int lift = id < 24 ? pulse : 0;
    const bool blink = id == DIZZY_FACE_IDLE && ms % 5300 >= 5160;
    p.ellipse(233,223,398,398,0x0B141D);
    p.ellipse(233,219,304,304,halo);
    p.ellipse(233,222,246,246,0x101D29);
    for (int side : {-1,1}) {
        int x = 233 + 75*side, y = 195 + lift;
        int w = 70, h = 91, radius = style == 1 ? 6 : 31;
        if (blink || (mood == 3 && side == 1)) h = 12;
        if (mood == 5) h = 22;
        if (mood == 6) { w += 7; h += 14; }
        if (mood == 2) { y += 12*side; h += 12*side; }
        if (mood == 1) { h = 51; y -= 8; }
        if (mood == 7) { h = 57; y += 4; }
        if (id == DIZZY_FACE_THINKING) y += side*7;
        if (id == DIZZY_FACE_RECORDING) { w += pulse; h += 2*pulse; }
        if (id == DIZZY_FACE_FAULT) h = 26;
        p.rect(x-w/2-3,y-h/2-3,w+6,h+6,radius+3,shade);
        if (mood == 4) p.star(x,y,34+pulse,bright);
        else if (mood == 7 && style != 1) p.heart(x,y,bright);
        else p.rect(x-w/2,y-h/2,w,h,std::min(radius,h/2),bright);
        if (h > 55 && mood != 4 && mood != 7) {
            int gaze = mood == 2 ? 11 : 0;
            p.ellipse(x+gaze,y+9,29,35,shade);
            p.ellipse(x+gaze-4,y+3,11,10,0xEDF9FE);
        }
        if (mood == 0 || mood == 1 || mood == 7) p.ellipse(x+side*18,261+lift,23,11,accent);
    }
    if (id == DIZZY_FACE_SPEAKING || mood == 6) {
        p.ellipse(233,273,31,31+(id==DIZZY_FACE_SPEAKING ? pulse*3 : 10),bright);
        p.ellipse(233,274,20,18,halo);
    } else if (mood == 5 || id == DIZZY_FACE_THINKING || id == DIZZY_FACE_FAULT) {
        p.rect(217,274,32,8,4,bright);
    } else {
        p.line(213,267,224,276,7,bright);
        p.line(224,276,243,276,7,bright);
        p.line(243,276,253,267,7,bright);
    }
    if (mood == 4 || style == 2) {
        p.star(115,125,8+pulse/2,accent);
        p.star(351,119,10+pulse/2,bright);
        p.star(326,302,8-pulse/2,accent);
    }
    if (id >= DIZZY_FACE_RECORDING) {
        auto signal = id == DIZZY_FACE_RECORDING || id == DIZZY_FACE_FAULT ? 0xF57065
            : id == DIZZY_FACE_ALARM ? 0xFFBF6A : bright;
        p.ellipse(233,112,12+2*pulse/3,12+2*pulse/3,signal);
    }
    if (introduction && id < 24) p.ellipse(233,102,8,8,accent);
    return p.size;
}
