/**
 * Project Rakshak: Edge-Intelligent Grid Resilience Controller
 * Platform: ESP32 DevKit V1 (FreeRTOS Native)
 * Aligned with SDG 11: Sustainable Cities & Communities
 * 
 * Features:
 * 1. Dual-Core architecture (Core 0: Telemetry; Core 1: Real-time relay FSM & RoCoF)
 * 2. Hardware MAC-hash decentralized staggered restoration (Anti-Rebound)
 * 3. Compressor lockout timer against short-cycling (Oyefeso et al., IEEE 2024)
 * 4. Priority-tiered load shedding:
 *    - Tier 0: Critical (Medical / LED) -> ALWAYS ENERGIZED
 *    - Tier 1: Essential (Fan) -> Shed on extreme dip
 *    - Tier 2: Deferrable (Heater / AC) -> First to shed
 */

#include <Arduino.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include "config.h"
#include "nilm_edge.h"

// State Machine Definitions
enum GridState {
    GRID_NORMAL,
    UNDER_FREQUENCY_TRIP,
    LOCKOUT_HOLD,
    STAGGERED_RESTORING
};

GridState currentState = GRID_NORMAL;

// Edge Telemetry Variables
float currentFrequency = 50.00;
float currentRoCoF = 0.00;
float measuredPowerW = 18.5; // Benchtop default

// Timing & Timers
unsigned long lastShedTimestamp = 0;
unsigned long recoveryStartTime = 0;
unsigned long calculatedStaggerDelayMs = 0;
uint32_t deviceMacHash = 0;

EdgeNILM nilm;

// FreeRTOS Task Handles
TaskHandle_t TaskTelemetryHandle;
TaskHandle_t TaskRelayLogicHandle;

// Function to calculate deterministic CRC32 hash from hardware MAC address
uint32_t computeMacHash() {
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    uint32_t crc = 0xFFFFFFFF;
    for (int i = 0; i < 6; i++) {
        crc ^= mac[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        }
    }
    return ~crc;
}

// ----------------------------------------------------
// CORE 1: High-Speed Protection & Relay FSM Task
// ----------------------------------------------------
void TaskRelayLogic(void *pvParameters) {
    for (;;) {
        unsigned long now = millis();

        // 1. Check for incoming Serial frequency packets from HIL simulation
        // Packet format: {"f": 49.52, "df": -0.35}
        if (Serial.available() > 0) {
            String line = Serial.readStringUntil('\n');
            line.trim();
            if (line.startsWith("{") && line.indexOf("\"f\":") != -1) {
                int f_idx = line.indexOf("\"f\":") + 4;
                float f_val = line.substring(f_idx, line.indexOf(",", f_idx)).toFloat();
                if (f_val > 40.0 && f_val < 60.0) {
                    float prev_f = currentFrequency;
                    currentFrequency = f_val;
                    currentRoCoF = (currentFrequency - prev_f) / 0.05; // 50ms interval
                }
            }
        }

        // 2. Evaluate Protection Rules
        bool severeRoCoF = (currentRoCoF <= SEVERE_ROCOF_HZ_S);
        bool underFreq = (currentFrequency <= SHED_THRESHOLD_HZ);

        switch (currentState) {
            case GRID_NORMAL:
                // Grid is healthy
                digitalWrite(PIN_RELAY_CRITICAL, LOW);    // Power ON (Active LOW)
                digitalWrite(PIN_RELAY_ESSENTIAL, LOW);   // Power ON
                digitalWrite(PIN_RELAY_DEFERRABLE, LOW);  // Power ON
                digitalWrite(PIN_LED_GRID_HEALTHY, HIGH);
                digitalWrite(PIN_LED_SHED_ACTIVE, LOW);

                if (underFreq || (severeRoCoF && currentFrequency < 49.80)) {
                    // Trigger Immediate Level 2 (Deferrable) Shedding
                    digitalWrite(PIN_RELAY_DEFERRABLE, HIGH); // Cut Deferrable Relay
                    digitalWrite(PIN_LED_SHED_ACTIVE, HIGH);
                    lastShedTimestamp = now;

                    // If frequency is severely low, shed Level 1 (Essential) as well
                    if (currentFrequency <= (SHED_THRESHOLD_HZ - 0.40)) {
                        digitalWrite(PIN_RELAY_ESSENTIAL, HIGH);
                    }

                    // Critical Life-Safety relay is NEVER cut!
                    digitalWrite(PIN_RELAY_CRITICAL, LOW);

                    currentState = UNDER_FREQUENCY_TRIP;
                }
                break;

            case UNDER_FREQUENCY_TRIP:
                // Check if grid has recovered above hysteresis boundary
                if (currentFrequency >= (SHED_THRESHOLD_HZ + HYSTERESIS_BAND_HZ)) {
                    recoveryStartTime = now;
                    // Calculate decentralized staggered restoration delay
                    // Uniform distribution across [2.0s, 35.0s] based on unique chip MAC
                    calculatedStaggerDelayMs = 2000 + (deviceMacHash % MAX_STAGGER_SPREAD_MS);
                    currentState = LOCKOUT_HOLD;
                }
                break;

            case LOCKOUT_HOLD:
                // Enforce compressor lockout protection (Oyefeso et al., IEEE 2024)
                if (now - lastShedTimestamp < COMPRESSOR_LOCKOUT_MS) {
                    // Still in thermal cooldown; keep deferrable relay open
                    digitalWrite(PIN_RELAY_DEFERRABLE, HIGH);
                } else {
                    currentState = STAGGERED_RESTORING;
                }
                break;

            case STAGGERED_RESTORING:
                // Staggered reconnection timer
                if (now - recoveryStartTime >= calculatedStaggerDelayMs) {
                    // Restore Essential loads first, then Deferrable
                    digitalWrite(PIN_RELAY_ESSENTIAL, LOW);
                    digitalWrite(PIN_RELAY_DEFERRABLE, LOW);
                    digitalWrite(PIN_LED_SHED_ACTIVE, LOW);
                    currentState = GRID_NORMAL;
                }
                break;
        }

        vTaskDelay(pdMS_TO_TICKS(20)); // Run at 50 Hz
    }
}

// ----------------------------------------------------
// CORE 0: Network & Telemetry Reporting Task
// ----------------------------------------------------
void TaskTelemetry(void *pvParameters) {
    for (;;) {
        // Construct JSON telemetry packet for Python Backend and Digital Twin
        // Format: {"node_id": "esp32_rakshak_01", "f": 49.65, "shed_l3": 1, "state": "NORMAL"}
        String statusJson = "{";
        statusJson += "\"node_id\":\"esp32_rakshak_01\",";
        statusJson += "\"f\":" + String(currentFrequency, 2) + ",";
        statusJson += "\"rocof\":" + String(currentRoCoF, 2) + ",";
        statusJson += "\"shed_l3\":" + String(digitalRead(PIN_RELAY_DEFERRABLE) == HIGH ? 1 : 0) + ",";
        statusJson += "\"shed_l2\":" + String(digitalRead(PIN_RELAY_ESSENTIAL) == HIGH ? 1 : 0) + ",";
        statusJson += "\"shed_l1\":0,"; // Always protected
        statusJson += "\"state\":" + String(currentState);
        statusJson += "}";

        Serial.println(statusJson);
        vTaskDelay(pdMS_TO_TICKS(100)); // 10 Hz telemetry
    }
}

void setup() {
    Serial.begin(115200);

    // Initialize Relay Pins
    pinMode(PIN_RELAY_CRITICAL, OUTPUT);
    pinMode(PIN_RELAY_ESSENTIAL, OUTPUT);
    pinMode(PIN_RELAY_DEFERRABLE, OUTPUT);
    pinMode(PIN_LED_GRID_HEALTHY, OUTPUT);
    pinMode(PIN_LED_SHED_ACTIVE, OUTPUT);

    // Initial Relay States: Powered ON (Active LOW relays)
    digitalWrite(PIN_RELAY_CRITICAL, LOW);
    digitalWrite(PIN_RELAY_ESSENTIAL, LOW);
    digitalWrite(PIN_RELAY_DEFERRABLE, LOW);
    digitalWrite(PIN_LED_GRID_HEALTHY, HIGH);
    digitalWrite(PIN_LED_SHED_ACTIVE, LOW);

    // Compute Hardware MAC Address Hash
    deviceMacHash = computeMacHash();

    // Pin FreeRTOS tasks to respective ESP32 cores
    xTaskCreatePinnedToCore(TaskRelayLogic, "RelayFSM", 4096, NULL, 2, &TaskRelayLogicHandle, 1);
    xTaskCreatePinnedToCore(TaskTelemetry,  "Telemetry", 4096, NULL, 1, &TaskTelemetryHandle,  0);
}

void loop() {
    // Empty; FreeRTOS tasks manage execution
    vTaskDelay(pdMS_TO_TICKS(1000));
}
