#ifndef NILM_EDGE_H
#define NILM_EDGE_H

#include <Arduino.h>

struct NILMState {
    float previous_power_w = 0.0;
    float current_power_w = 0.0;
    float delta_power_w = 0.0;
    bool fan_active = false;
    bool heater_active = false;
    bool ac_active = false;
};

class EdgeNILM {
public:
    NILMState state;

    void update(float measured_w) {
        state.previous_power_w = state.current_power_w;
        state.current_power_w = measured_w;
        state.delta_power_w = state.current_power_w - state.previous_power_w;

        // Positive Step Detection (Appliance turned ON)
        if (state.delta_power_w > 8.0) {
            if (state.delta_power_w >= 10.0 && state.delta_power_w < 25.0) {
                state.heater_active = true; // 12V benchtop heating pad (~15W)
            } else if (state.delta_power_w >= 4.0 && state.delta_power_w < 10.0) {
                state.fan_active = true;    // 12V cooling fan (~5W)
            }
        }
        // Negative Step Detection (Appliance turned OFF)
        else if (state.delta_power_w < -8.0) {
            float abs_drop = fabs(state.delta_power_w);
            if (abs_drop >= 10.0 && abs_drop < 25.0) {
                state.heater_active = false;
            } else if (abs_drop >= 4.0 && abs_drop < 10.0) {
                state.fan_active = false;
            }
        }
    }
};

#endif // NILM_EDGE_H
