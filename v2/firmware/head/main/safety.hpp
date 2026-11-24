#pragma once
// Hardware-independent safety decisions for the Dizzy V2 head firmware.
// main.cpp calls these; test/safety_test.cpp exercises them on a host compiler.
// A host pass does not validate the physical robot: sensors, power and motors still need bench tests.
namespace dizzy_safety {

constexpr float kMinBatteryVolts = 6.8f;
constexpr float kArmMaxTiltDegrees = 12.0f;      // upright limit to arm or to clear a latched fault
constexpr float kLatchTiltDegrees = 38.0f;       // armed robot beyond this tilt latches a stop

inline bool battery_ok(float volts) { return volts >= kMinBatteryVolts; }

// read_imu(tilt) returns false when the IMU read fails. It is only called when the earlier checks pass.
// NaN tilt is treated as unsafe.
template <class ReadImu>
bool can_clear_fault(bool io_ready, bool stop_switch_pressed, float battery_volts, ReadImu read_imu) {
    float tilt = 0.0f;
    if (!io_ready || stop_switch_pressed || !battery_ok(battery_volts)) return false;
    if (!read_imu(tilt)) return false;
    return tilt <= kArmMaxTiltDegrees;
}

template <class ReadImu>
bool can_floor_arm(bool io_ready, bool stop_switch_pressed, bool ringing, bool quiet, float battery_volts,
                   bool both_feet_down, ReadImu read_imu) {
    float tilt = 0.0f;
    if (!io_ready || stop_switch_pressed || ringing || quiet || !battery_ok(battery_volts)) return false;
    if (!read_imu(tilt) || !(tilt <= kArmMaxTiltDegrees)) return false;
    return both_feet_down;
}

inline bool should_latch_stop(bool imu_ok, float tilt, float battery_volts) {
    return !imu_ok || !(tilt <= kLatchTiltDegrees) || !battery_ok(battery_volts);
}

inline bool motion_allowed(bool io_ready, bool motor_fault, bool stop_switch_pressed, float battery_volts,
                           bool quiet, bool ringing) {
    return io_ready && !motor_fault && !stop_switch_pressed && battery_ok(battery_volts) && !quiet && !ringing;
}

inline bool servo_power_allowed(bool io_ready, bool stop_switch_pressed, bool motor_fault, float battery_volts) {
    return io_ready && !stop_switch_pressed && !motor_fault && battery_ok(battery_volts);
}

}  // namespace dizzy_safety
