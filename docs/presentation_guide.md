# Project Rakshak: Phase-2 Evaluator Presentation & Viva Guide

Use this guide when presenting Phase 2 to your professors and evaluators.

---

## 1. The 60-Second Opening Pitch

> *"Respected evaluators, think of the electrical grid as a massive see-saw. On one side is electricity generation; on the other is urban demand. For the grid to function, both sides must balance at 50 Hz.*
> 
> *In solar-rich smart cities like Bengaluru, rooftop solar generation can drop suddenly due to cloud cover or feeder faults. Today, when supply falls, utilities execute **Substation Under-Frequency Load Shedding (UFLS)**. They cut power indiscriminately to entire neighborhoods—cutting off oxygen concentrators, hospital clinics, and school lights alongside air conditioners and water heaters. **In simple words: when the grid is in trouble, today's system switches off people, not appliances.***
> 
> *Our project, **Rakshak**, decentralizes protection to the building edge. Using an ESP32 controller and single-sensor Non-Intrusive Load Monitoring (NILM), Rakshak detects under-frequency events locally. It immediately sheds non-essential deferrable loads like ACs and EV chargers, while guaranteeing that critical life-safety loads remain powered. In Phase 2, we have developed the complete Digital Twin, swing-equation co-simulation engine, and multi-agent fleet model."*

---

## 2. Live Demo Script (3-Minute Walkthrough)

### Step 1: Open the 3D Digital Twin
1. Run `python run_sim.py` (or open `frontend/index.html`).
2. Show the street with 12 buildings, the local distribution transformer, and the clinic with the medical cross.

### Step 2: Act 1 – The Failure of Conventional Feeder UFLS
1. Set the dropdown to **"2. Substation UFLS (Feeder Tripping)"**.
2. Click **Restart** and let time reach $t = 5.0\text{ s}$.
3. **What happens:** The generation drops by 18%. Frequency drops below $49.2\text{ Hz}$.
4. **Point to the screen:** The substation breaker trips Feeder 1. The clinic goes completely black. Focus on the clinic inside: the patient monitor flatlines with a red **"CRITICAL: NO POWER"** warning.

### Step 3: Act 2 – Project Rakshak in Action
1. Switch the dropdown to **"3. Rakshak DR (MAC-Hash Staggered)"**.
2. Click **Restart**.
3. At $t = 5.0\text{ s}$, frequency dips.
4. **Point to the screen:** The rooftop AC fans stop, and water heaters are shed. **Crucially: the clinic windows stay illuminated, the LED lights remain on, and the patient monitor continues running normally.**
5. Point out that the frequency nadir is raised from $48.88\text{ Hz}$ to $49.46\text{ Hz}$.

### Step 4: Act 3 – Eliminating the Rebound Peak
1. Compare Mode 3 vs Mode 4 (**"4. Rakshak DR (No Staggering)"**).
2. Show how Mode 4 causes a **165% secondary demand spike** when all ACs restart together.
3. Show how Mode 3 uses the **MAC-hash staggered restoration algorithm** to flatten the curve to **115%**.

---

## 3. Anticipated Viva Questions & Strong Answers

### Q1: "Why use the MAC address hash instead of a standard `rand()` function?"
* **Answer:** *"Standard pseudo-random number generators on microcontrollers require a unique seed, often derived from an RTC or floating ADC pin, which can produce identical or correlated numbers across devices after a simultaneous brownout. The 48-bit IEEE hardware MAC address is physically unique, burnt into the silicon at manufacture. Hashing the MAC address (`CRC32(MAC)`) guarantees a deterministic, uniform, and non-colliding delay for every home without requiring any internet communication."*

### Q2: "How does this compare to existing smart home energy management (HEMS)?"
* **Answer:** *"Most HEMS solutions focus on economic optimization—shifting loads based on time-of-day tariffs over hours. Rakshak is an emergency, sub-second protection system designed for grid frequency stability. It operates in milliseconds directly at the electrical edge to avert cascading city-wide blackouts."*

### Q3: "How does the research paper by Oyefeso et al. (IEEE 2024) support your work?"
* **Answer:** *"Oyefeso et al. at Los Alamos proved two critical physical principles that we incorporated: First, AC compressors have a strict ~3-minute lockout time to prevent motor burnout, which we modeled in our firmware and digital twin. Second, centralized load control suffered severe degradation under communication latency and packet loss. Our decentralized edge-based approach requires zero communication network bandwidth during disasters."*

### Q4: "What is your plan for Phase 3?"
* **Answer:** *"In Phase 3, we connect our physical ESP32 breadboard prototype to this software environment using the `HILBridge` we already developed. The ESP32 will control 12V low-voltage proxy loads (fan, heating pad, LED) using relays, while reading simulated frequency over serial to demonstrate physical Hardware-in-the-Loop operation."*
