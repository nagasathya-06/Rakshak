#ifndef RAKSHAK_CONFIG_H
#define RAKSHAK_CONFIG_H

#include <Arduino.h>

// ==========================================
// PIN DEFINITIONS FOR SAFE LOW-VOLTAGE DEMO
// ==========================================
// Relay outputs (Active LOW for standard optocoupled relay modules)
#define PIN_RELAY_CRITICAL     18  // Tier 0: Life-Safety (LED / O2 Concentrator) - Normally CLOSED
#define PIN_RELAY_ESSENTIAL    19  // Tier 1: Essential (DC Fan)
#define PIN_RELAY_DEFERRABLE   23  // Tier 2: Deferrable (Heating Pad / AC proxy)

// Status Indicator LEDs
#define PIN_LED_GRID_HEALTHY   2   // Built-in Blue LED (Grid Normal)
#define PIN_LED_SHED_ACTIVE    4   // Red LED (Load Shed Active)

// Zero-Crossing or Frequency Sensor Input (Optional AC stretch goal)
#define PIN_ZERO_CROSS_INT     34

// ==========================================
// THRESHOLDS & CONSTANTS
// ==========================================
#define NOMINAL_FREQ_HZ         50.00
#define SHED_THRESHOLD_HZ       49.60   // Primary Rakshak shedding threshold
#define RECOVERY_THRESHOLD_HZ   49.90   // Grid deemed recovered
#define HYSTERESIS_BAND_HZ      0.15    // Prevents relay flapping
#define SEVERE_ROCOF_HZ_S      -0.50    // Predictive fast-collapse trigger

#define COMPRESSOR_LOCKOUT_MS   15000   // 15 seconds in benchtop demo (3 min in real world)
#define MAX_STAGGER_SPREAD_MS   35000   // Uniform delay window for MAC-hash recovery

#endif // RAKSHAK_CONFIG_H
