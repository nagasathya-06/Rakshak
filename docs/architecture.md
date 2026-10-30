# Project Rakshak: System & Software Architecture

## 1. The Distributed System View
In traditional electrical grids, control is centralized and slow. Substation SCADA systems observe feeder overloads or frequency drops and trip distribution breakers en masse.

**Project Rakshak** reframes the distribution grid as an **Edge-Computing Multi-Agent System**:
* Every building is an autonomous **Edge Agent** powered by an ESP32.
* The grid's alternating frequency ($50.0\text{ Hz}$ in India) acts as a **global, zero-latency physical clock / broadcast bus**.
* Agents make localized decisions without requiring continuous, vulnerable network communication with a centralized cloud.

```
                                  [ Power Grid Physics ]
                             Frequency Drop: f <= 49.60 Hz
                                           │
             ┌─────────────────────────────┼─────────────────────────────┐
             ▼                             ▼                             ▼
   [ Building Agent #1 ]         [ Building Agent #2 ]         [ Building Agent #N ]
     (ESP32 Controller)            (ESP32 Controller)            (ESP32 Controller)
             │                             │                             │
    NILM Disaggregation           NILM Disaggregation           NILM Disaggregation
             │                             │                             │
    Selective Priority Trip       Selective Priority Trip       Selective Priority Trip
    (Shed AC, Keep O2 ON)         (Shed EV, Keep Lights ON)     (Shed Heater, Keep Fridge ON)
             │                             │                             │
    MAC-Hash Restore Timer        MAC-Hash Restore Timer        MAC-Hash Restore Timer
    Delay: 12.4s                  Delay: 28.1s                  Delay: 6.7s
```

---

## 2. Mathematical Formulations

### A. Grid Swing Equation
The rate of change of grid frequency deviation $x = \frac{f - f_0}{f_0}$ is modeled as:
$$\frac{dx}{dt} = \frac{1}{2H} \left( P_m + P_g - P_e - D \cdot x \right)$$

Where:
* $f_0 = 50.0\text{ Hz}$ (Nominal synchronous frequency)
* $H = 5.0\text{ s}$ (Inertia constant of rotating turbines & synchronous generators)
* $D = 1.0$ (Load-damping factor)
* $P_m$ = Mechanical/solar generation schedule (in per-unit)
* $P_g$ = Primary turbine governor power adjustment
* $P_e$ = Aggregate electrical demand (in per-unit)

### B. Rate of Change of Frequency (RoCoF)
$$\text{RoCoF} = \frac{df}{dt} \approx \frac{f(t) - f(t - \Delta t)}{\Delta t}$$
If $\text{RoCoF} \le -0.50\text{ Hz/s}$, the edge node detects an abrupt generation loss and triggers predictive early shedding before the static $49.6\text{ Hz}$ threshold is breached.

### C. Transient Inrush & Cold-Load Pickup
Loads draw an instantaneous surge upon connection:
$$P(t) = P_{\text{steady}} \cdot \left(1 + (k_{\text{inrush}} - 1) e^{-\frac{t - t_{\text{on}}}{\tau}}\right)$$
* Compressor loads (ACs): $k_{\text{inrush}} \approx 3.0\times\text{ to }6.0\times$
* Resistive loads (Heaters): $k_{\text{inrush}} \approx 1.1\times$

### D. Decentralized MAC-Hash Staggered Restoration
To prevent simultaneous reconnection surges, each node uses its 48-bit hardware MAC address to calculate a deterministic delay:
$$\text{Delay}_i = T_{\text{base}} + \left( \text{CRC32}(\text{MAC}_i \parallel \text{DeviceKey}) \bmod T_{\text{spread}} \right)$$
This yields a **uniform random distribution** across the restoration window, flattening the aggregate demand curve without requiring central coordination.

---

## 3. The 3-Tier Priority Matrix

| Tier | Priority | Appliances | Action During Under-Frequency ($f \le 49.6\text{ Hz}$) |
| :--- | :--- | :--- | :--- |
| **Tier 0** | **Critical (Life-Safety)** | Oxygen Concentrators, Patient Monitors, Medicine Refrigeration, Security Lights | **Guaranteed ALWAYS ON**. Never interrupted by the edge relay. |
| **Tier 1** | **Essential** | Ceiling Fans, Basic Lighting, Ventilation | Kept ON during moderate disturbances; shed only during extreme collapses ($f < 49.2\text{ Hz}$). |
| **Tier 2** | **Deferrable** | Air Conditioners, Water Heaters, EV Fast Chargers | **Shed immediately within 50ms**. Subject to compressor lockout cooldown. |
