# Project Rakshak: ESP32 Edge Firmware

This directory contains the production-grade FreeRTOS C++ firmware for the **ESP32 DevKit V1** edge load controller.

---

## Hardware Architecture

```
                       ┌─────────────────────────┐
                       │     ESP32 DEVKIT V1     │
                       │                         │
  [Zero-Crossing / ───►│ GPIO 34 (Timer Capture) │
   HIL Serial Stream]  │                         │
                       │ GPIO 18 (Active LOW) ───┼──► Relay 1: Critical (LED / O2 Monitor)
  [INA219 I2C Bus] ───►│ GPIO 21 (SDA), 22 (SCL) │──► Relay 2: Essential (DC Fan)
                       │ GPIO 23 (Active LOW) ───┼──► Relay 3: Deferrable (Heating Pad / AC)
                       │                         │
                       │ GPIO 2  (Blue LED) ─────┼──► Status: Grid Healthy (50.0 Hz)
                       │ GPIO 4  (Red LED) ──────┼──► Status: Load Shed Active (<49.6 Hz)
                       └─────────────────────────┘
```

---

## FreeRTOS Dual-Core Allocation

* **Core 1 (Real-Time Safety & Protection):**
  * Evaluates grid frequency every $20\text{ ms}$ ($50\text{ Hz}$).
  * Computes Rate of Change of Frequency ($\text{RoCoF} = \frac{df}{dt}$).
  * Controls optocoupled relay switching state machine.
  * Implements **Compressor Lockout Protection** ($15\text{s}$ cooldown to prevent short-cycling).
  * Executes **Decentralized MAC-Hash Delay** for staggered restoration.

* **Core 0 (Networking & Telemetry):**
  * Serial and Wi-Fi telemetry reporting at $10\text{ Hz}$ to the Python backend and Digital Twin.
  * Ensures telemetry overhead never blocks real-time relay trip speed.

---

## Pinout Map

| ESP32 GPIO | Function | Connected Component | State in Normal Grid | State in Grid Collapse |
| :--- | :--- | :--- | :--- | :--- |
| **GPIO 18** | Relay 1 (Tier 0) | Life-Safety / Critical Load (LED / O2) | LOW (Energized) | **LOW (Kept ALWAYS ON)** |
| **GPIO 19** | Relay 2 (Tier 1) | Essential Load (Cooling Fan) | LOW (Energized) | HIGH (Shed if $f < 49.2\text{ Hz}$) |
| **GPIO 23** | Relay 3 (Tier 2) | Deferrable Load (Heating Pad) | LOW (Energized) | HIGH (Shed if $f \le 49.6\text{ Hz}$) |
| **GPIO 2** | LED Indicator | Built-in Blue LED | HIGH (Normal) | LOW |
| **GPIO 4** | LED Indicator | Red Alert LED | LOW | HIGH (Shed Active) |
| **GPIO 21 / 22** | I2C Bus | INA219 Voltage & Current Monitor | Continuous sampling | Continuous sampling |

---

## Benchtop Safety Rule
All demonstrations are conducted using **low-voltage 12V DC power or 5V LEDs**. Mains AC (230V) is never switched directly on breadboards or student benches.
