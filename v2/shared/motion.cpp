#include "motion.h"
#include <algorithm>
#include <cmath>

void dizzy_pose(int action, double elapsed, double bpm, float *degrees) {
    std::fill(degrees,degrees+8,0.f);
    constexpr double tau = 6.283185307179586;
    double t = std::max(elapsed,0.0);
    double phase = t * tau * std::clamp(bpm, 60.0, 130.0) / 120.0;
    double s = std::sin(phase), c = std::cos(phase);
    double fade = std::min(t/.40,1.0);
    switch (action) {
        case DIZZY_WAVE: degrees[3] = 64 + 20*s; break;
        case DIZZY_SWAY:
            degrees[0] = 20*s; degrees[1] = 6*c;
            degrees[2] = 18+13*s; degrees[3] = 18-13*s;
            degrees[6] = degrees[7] = 11*s; break;
        case DIZZY_HEEL:
            degrees[1] = 10*c; degrees[2] = 41+26*s; degrees[3] = 41-26*s;
            degrees[6] = 14*std::max(0.0,s); degrees[7] = -14*std::max(0.0,-s); break;
        case DIZZY_BOUNCE:
            degrees[0] = 15*s; degrees[1] = 12*std::sin(2*phase);
            degrees[2] = degrees[3] = 28+19*c;
            degrees[6] = 10*s; degrees[7] = 10*s; break;
        case DIZZY_SHUFFLE:
            degrees[4] = 13.4*c; degrees[5] = -13.4*c;
            degrees[6] = (s>=0 ? 18 : 11)*s;
            degrees[7] = (s>=0 ? 11 : 18)*s; break;
    }
    for (int i=0;i<8;++i) degrees[i] *= fade;
}
