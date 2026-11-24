#pragma once
#ifdef __cplusplus
extern "C" {
#endif
enum { DIZZY_REST, DIZZY_WAVE, DIZZY_SWAY, DIZZY_HEEL, DIZZY_BOUNCE, DIZZY_SHUFFLE };
/* yaw, pitch, left arm, right arm, left hip, right hip, left ankle, right ankle */
void dizzy_pose(int action, double elapsed, double bpm, float *degrees);
#ifdef __cplusplus
}
#endif
