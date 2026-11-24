#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum { DIZZY_FACE_COUNT = 24, DIZZY_FACE_IDLE = 24, DIZZY_FACE_RECORDING,
    DIZZY_FACE_THINKING, DIZZY_FACE_SPEAKING, DIZZY_FACE_ALARM, DIZZY_FACE_FAULT };
enum { DIZZY_RECT, DIZZY_ELLIPSE, DIZZY_LINE };
typedef struct {
    int16_t kind, x, y, a, b, radius;
    uint32_t color;
} DizzyShape;

const char *dizzy_face_name(int id);
const char *dizzy_face_style(int id);
int dizzy_face(int id, int phase_ms, DizzyShape *out, int capacity);

#ifdef __cplusplus
}
#endif
