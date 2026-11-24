// Host test for main/safety.hpp. Build: g++ -std=c++17 -I../main safety_test.cpp -o safety_test
#include "safety.hpp"
#include <cmath>
#include <cstdio>
#include <limits>

using namespace dizzy_safety;
static int failures = 0;
#define CHECK(cond) do { if(!(cond)) { std::printf("FAIL line %d: %s\n", __LINE__, #cond); ++failures; } } while(0)

static auto imu(float tilt, bool ok = true) { return [=](float &t) { t = tilt; return ok; }; }
static bool called;
static auto spy(float tilt) { return [=](float &t) { called = true; t = tilt; return true; }; }
static const float kNaN = std::numeric_limits<float>::quiet_NaN();

int main() {
    // clear fault
    CHECK(can_clear_fault(true, false, 7.4f, imu(0)));
    CHECK(can_clear_fault(true, false, 7.4f, imu(12.0f)));
    CHECK(!can_clear_fault(true, false, 7.4f, imu(12.01f)));
    CHECK(!can_clear_fault(true, false, 7.4f, imu(90)));
    CHECK(!can_clear_fault(true, false, 7.4f, imu(0, false)));          // IMU read failed
    CHECK(!can_clear_fault(true, false, 7.4f, imu(kNaN)));
    CHECK(!can_clear_fault(true, true, 7.4f, imu(0)));                  // stop switch pressed
    CHECK(!can_clear_fault(false, false, 7.4f, imu(0)));                // IO not ready
    CHECK(can_clear_fault(true, false, 6.8f, imu(0)));
    CHECK(!can_clear_fault(true, false, 6.79f, imu(0)));
    CHECK(!can_clear_fault(true, false, kNaN, imu(0)));
    called = false; CHECK(!can_clear_fault(true, true, 7.4f, spy(0))); CHECK(!called);   // IMU not read when blocked
    called = false; CHECK(can_clear_fault(true, false, 7.4f, spy(0))); CHECK(called);

    // floor arm
    CHECK(can_floor_arm(true, false, false, false, 7.4f, true, imu(5)));
    CHECK(!can_floor_arm(true, false, false, false, 7.4f, false, imu(5)));   // feet not both down
    CHECK(!can_floor_arm(true, false, true, false, 7.4f, true, imu(5)));     // alarm ringing
    CHECK(!can_floor_arm(true, false, false, true, 7.4f, true, imu(5)));     // quiet mode
    CHECK(!can_floor_arm(true, true, false, false, 7.4f, true, imu(5)));
    CHECK(!can_floor_arm(false, false, false, false, 7.4f, true, imu(5)));
    CHECK(!can_floor_arm(true, false, false, false, 6.7f, true, imu(5)));
    CHECK(!can_floor_arm(true, false, false, false, 7.4f, true, imu(13)));
    CHECK(!can_floor_arm(true, false, false, false, 7.4f, true, imu(5, false)));
    CHECK(!can_floor_arm(true, false, false, false, 7.4f, true, imu(kNaN)));

    // latch stop while armed
    CHECK(!should_latch_stop(true, 0, 7.4f));
    CHECK(!should_latch_stop(true, 38.0f, 7.4f));
    CHECK(should_latch_stop(true, 38.01f, 7.4f));
    CHECK(should_latch_stop(false, 0, 7.4f));
    CHECK(should_latch_stop(true, 0, 6.79f));
    CHECK(should_latch_stop(true, kNaN, 7.4f));
    CHECK(should_latch_stop(true, 0, kNaN));

    // motion and servo power gates
    CHECK(motion_allowed(true, false, false, 7.4f, false, false));
    CHECK(!motion_allowed(false, false, false, 7.4f, false, false));
    CHECK(!motion_allowed(true, true, false, 7.4f, false, false));
    CHECK(!motion_allowed(true, false, true, 7.4f, false, false));
    CHECK(!motion_allowed(true, false, false, 6.7f, false, false));
    CHECK(!motion_allowed(true, false, false, 7.4f, true, false));
    CHECK(!motion_allowed(true, false, false, 7.4f, false, true));
    CHECK(servo_power_allowed(true, false, false, 7.4f));
    CHECK(!servo_power_allowed(false, false, false, 7.4f));
    CHECK(!servo_power_allowed(true, true, false, 7.4f));
    CHECK(!servo_power_allowed(true, false, true, 7.4f));
    CHECK(!servo_power_allowed(true, false, false, 6.79f));

    if (failures) { std::printf("%d check(s) failed\n", failures); return 1; }
    std::printf("safety_test: all checks passed\n");
    return 0;
}
