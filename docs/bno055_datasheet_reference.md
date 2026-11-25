# BNO055: datasheet reference

A condensed version of the Bosch BNO055 datasheet, organized by the questions that come up when using the chip for navigation. Every claim cites the page where it can be checked.

| Tag | Source |
|---|---|
| DS | Bosch Sensortec, *BNO055 Data sheet*, BST-BNO055-DS000-18, rev 1.8, Oct 2021 — <https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bno055-ds000.pdf> |

Legend: `p.N` is the PDF page index. In this datasheet it matches the printed "Page N" header, so it works as a jump target in any PDF viewer.

---

## 1. What the chip is

- A system-in-package that combines a 14-bit accelerometer, a 16-bit gyroscope, a geomagnetic sensor and a 32-bit Cortex-M0+ running Bosch's sensor-fusion firmware (p.4).
- The sensors talk to the internal MCU over SPI. The host talks only to the MCU, over I²C, UART or HID-I²C, plus an INT line (p.19, Fig. 1).
- Two supplies: VDD powers the sensors and VDDIO powers the MCU and I/O. VDD must come up **before or at the same time as** VDDIO (p.19).

## 2. Limits that matter for navigation

| # | Fact | Ref |
|---|---|---|
| 1 | The fusion was designed for **human motion**. Sustained acceleration (vehicle cornering, long braking) can be mistaken for gravity, which corrupts pitch and roll. Bosch says to test for the specific use case. | p.24 |
| 2 | While the device moves, the fusion ignores the accelerometer and tracks pitch and roll from the gyro alone. Long vibration or constant motion therefore lets pitch and roll drift. | p.24 |
| 3 | When the magnetometer is judged distorted, it is ignored and heading drifts as in IMU mode. | p.24 |
| 4 | Linear acceleration **cannot be integrated** into velocity or position. The error exceeds the signal in under 1 s unless other sensors correct it. | p.38 |
| 5 | Background auto-calibration is always on, **cannot be disabled**, and overwrites any calibration profile you load. | p.24, p.51, p.53 |
| 6 | Heading accuracy is ±2.5° typ, assuming a fully calibrated sensor, ideal tilt compensation and a 30 µT horizontal field. | p.16 |
| 7 | The maximum fusion output rate is 100 Hz (IMU, NDOF). Mag data arrives at only 20 Hz. | p.33 |
| 8 | The legal disclaimer classes it as a consumer product: not for safety-critical, military, deep-sea, **space or satellite** use. | p.115 |

## 3. Electrical and power

| Parameter | Value | Ref |
|---|---|---|
| VDD (sensors) | 2.4–3.6 V; abs. max 4.2 V | p.13, p.18 |
| VDDIO (MCU, I/O) | 1.7–3.6 V; abs. max 3.6 V; logic pins ≤ VDDIO+0.3 V | p.13, p.18 |
| Current, normal, 9DOF at 100 Hz | ≤ 12.3 mA | p.13 |
| Current, low-power / suspend | 0.33 mA (2.72 mA avg with 20 % active) / 0.04 mA | p.13 |
| Operating temperature | −40…+85 °C | p.13 |
| Shock | 10 000 g for 200 µs; 2 000 g for 1 ms; 1.8 m drop | p.18 |
| Power off → CONFIGMODE | 400 ms | p.14 |
| Reset → CONFIGMODE (POR) | 650 ms | p.14 |
| Reset triggers | nRESET low ≥ 20 ns, or `SYS_TRIGGER.RST_SYS` | p.19 |

**Power modes** (`PWR_MODE` 0x3E, bits 1:0) (p.20–21):
- `00` normal: every sensor the operating mode needs stays on.
- `01` low power: after no motion (default 5 s), only the accel stays on, and an any-motion event wakes the system. Only no-motion and any-motion interrupts work in this mode, and it is unavailable when the accel is not used.
- `10` suspend: sensors and MCU sleep and registers stop updating. Exit by writing `PWR_MODE`.
- `11` is invalid and must not be written.

**Board wiring for I²C** (p.106–107):
- 100 nF from VDD to GND and 120 nF from VDDIO to GNDIO.
- 1 µF from CAP (pin 9) to ground.
- 10 kΩ pull-up on nBOOT_LOAD_PIN (pin 4); low at reset enters the bootloader (p.51).
- Optional 10 kΩ pull-up on nRESET (pin 11).
- PS0/PS1 and COM2 tied to GNDIO.
- Leave pins 1, 12, 13, 15, 16 and 21–24 unconnected.

## 4. Sensor performance

| Sensor | Key figures | Ref |
|---|---|---|
| Accel | ±2/4/8/16 g; 1 LSB/mg; zero-g offset ±80 mg typ, ±150 mg max; offset tempco ±1 mg/K (max 3.5); noise 150 µg/√Hz; BW 8–1000 Hz; cross-axis 1 %; alignment 0.5° | p.14–15 |
| Gyro | ±125…±2000 °/s; 16 LSB/(°/s) = 900 LSB/(rad/s); zero-rate offset ±1 °/s typ, ±3 °/s max; offset tempco ±0.015 °/s/K; noise 0.1 °/s rms at 47 Hz (0.014 °/s/√Hz); BW 12–523 Hz | p.15–16 |
| Mag | ±1300 µT (x, y), ±2500 µT (z); 0.3 µT resolution; offset ±40 µT raw, ±2 µT after fusion calibration; offset tempco ±0.23 µT/K; gain error ±5 %; noise from 0.3 µT (high accuracy) to 1.0/1.4 µT (low power) | p.16–17 |

## 5. Operating modes

`OPR_MODE` 0x3D, bits 3:0. CONFIG→other takes **7 ms**; other→CONFIG takes **19 ms** (p.22). Sensors the mode does not use are suspended (p.21).

| Value | Mode | Sensors | Output | Fusion rate | Ref |
|---|---|---|---|---|---|
| 0x0 | CONFIGMODE | — | outputs zeroed, fusion halted; default after POR | — | p.23 |
| 0x1–0x7 | ACCONLY, MAGONLY, GYROONLY, ACCMAG, ACCGYRO, MAGGYRO, AMG | as named | raw, uncompensated | — | p.23 |
| 0x8 | IMU | A+G | relative orientation | 100 Hz | p.24, p.33 |
| 0x9 | COMPASS | A+M | absolute heading; needs mag calibration | 20 Hz | p.24, p.33 |
| 0xA | M4G | A+M | relative orientation; the mag replaces the gyro, so no gyro drift; no mag calibration | 50 Hz | p.24, p.33 |
| 0xB | NDOF_FMC_OFF | A+M+G | absolute orientation; slow mag calibration | 100 Hz | p.25 |
| 0xC | NDOF | A+M+G | absolute orientation; fast mag calibration, slightly more current | 100 Hz | p.25 |

- Most writable registers can be changed only in CONFIGMODE. `OPR_MODE` and the interrupt registers are the exceptions (p.23).
- In fusion modes the fusion owns the sensor configuration (§6). User sensor settings take effect only in non-fusion modes (p.28).

## 6. Sensor configuration (register page 1)

The defaults the fusion uses (p.28):
- Accel: normal, ±4 g, 62.5 Hz.
- Gyro: normal, 2000 °/s, 32 Hz.
- Mag: forced mode, 20 Hz, XY repetitions 15, Z repetitions 16.

| Register | Layout | Values | Ref |
|---|---|---|---|
| `ACC_Config` 0x08 (reset 0x0D) | [7:5] power · [4:2] BW · [1:0] range | range 2/4/8/16 g; BW 7.81, 15.63, 31.25, 62.5, 125, 250, 500, 1000 Hz; power normal, suspend, LP1, standby, LP2, deep suspend | p.29, p.87 |
| `MAG_Config` 0x09 (reset 0x0B) | [6:5] power · [4:3] operating mode · [2:0] ODR | ODR 2, 6, 8, 10, 15, 20, 25, 30 Hz; mode low-power, regular, enhanced, high-accuracy; power normal, sleep, suspend, force | p.31, p.87 |
| `GYR_Config_0` 0x0A (reset 0x38) | [5:3] BW · [2:0] range | range 2000…125 °/s; BW codes 0–7 = 523, 230, 116, 47, 23, 12, 64, 32 Hz (not monotonic) | p.30, p.88 |
| `GYR_Config_1` 0x0B | [2:0] power | normal, fast power-up, deep suspend, suspend, advanced power-save | p.30, p.88 |
| `ACC_Sleep_Config` 0x0C / `GYR_Sleep_Config` 0x0D | sleep timing | non-fusion modes only | p.89–90 |

In BNO low-power mode the firmware forces the accel power mode to normal (p.29).

## 7. Output data

**Reads.** Burst-read the data block. A multi-byte read returns a shadowed, consistent sample, while single-byte reads can mix the LSB and MSB of different samples (p.39).

**Data block, page 0.** 0x08–0x34 is 45 contiguous bytes. All values are int16, little-endian (p.55–58):

| Addr | Data | Scaling | Ref |
|---|---|---|---|
| 0x08 | ACC x, y, z | 100 LSB = 1 m/s², or 1 LSB = 1 mg | p.33, p.35 |
| 0x0E | MAG x, y, z | 16 LSB = 1 µT | p.34 |
| 0x14 | GYR x, y, z | 16 LSB = 1 °/s, or 900 LSB = 1 rad/s | p.35 |
| 0x1A | EUL **heading, roll, pitch** (in that order) | 16 LSB = 1°, or 900 LSB = 1 rad | p.37, p.66–67 |
| 0x20 | QUA w, x, y, z | 2¹⁴ LSB = 1 | p.37 |
| 0x28 | LIA (linear accel) x, y, z | same as ACC | p.38 |
| 0x2E | GRV (gravity) x, y, z | same as ACC | p.38 |
| 0x34 | TEMP (int8) | 1 LSB = 1 °C, or 1 LSB = 2 °F; source accel (`TEMP_SOURCE`=0) or gyro (1) | p.39 |

- In non-fusion modes ACC, MAG and GYR are uncompensated. In fusion modes they are offset-compensated (p.35–36).
- EUL, QUA, LIA and GRV exist only in fusion modes (p.37–38).

**`UNIT_SEL` 0x3B** (reset **0x80**) (p.32, p.75):
- bit0: accel, 0 = m/s², 1 = mg.
- bit1: gyro, 0 = °/s, 1 = rad/s.
- bit2: Euler, 0 = degrees, 1 = radians.
- bit4: temperature, 0 = °C, 1 = °F.
- bit7: orientation format, 0 = Windows, 1 = **Android (the default)**.

**Angle conventions** (p.32):
- Heading/yaw: 0…360°, increasing clockwise.
- Roll: −90…+90°.
- Pitch: ±180°. Turning clockwise *increases* it in the Windows format and *decreases* it in the Android format.

**Axis remap** (p.26–27, p.77):
- `AXIS_MAP_CONFIG` 0x41 (reset 0x24): [5:4] = Z source, [3:2] = Y source, [1:0] = X source. Codes are 00 = X, 01 = Y, 10 = Z. Assigning the same source axis twice is rejected and the previous value is kept.
- `AXIS_MAP_SIGN` 0x42: bit2 flips X, bit1 flips Y, bit0 flips Z.
- Ready-made placements (CONFIG/SIGN pairs):
  - Top-side mount: P0 0x21/0x04, P1 0x24/0x00 (default), P2 0x24/0x06, P3 0x21/0x02.
  - Bottom-side mount: P4 0x24/0x03, P5 0x21/0x01, P6 0x21/0x07, P7 0x24/0x05.
- The default frame is right-handed: X and Y lie in the package plane and Z points out of the top.

## 8. Calibration

- **Status.** `CALIB_STAT` 0x35: [7:6] SYS, [5:4] GYR, [3:2] ACC, [1:0] MAG. 0 means uncalibrated and 3 means fully calibrated. SYS applies only to absolute-orientation modes (p.73).
- **Motions.** Repeat these after every POR unless you restore a profile (p.51–52):
  - Gyro: hold the device still for a few seconds.
  - Accel: hold 6 different stable positions for a few seconds each, move slowly between them, and lie perpendicular to each axis at least once.
  - Mag: make random movements such as a figure-8. NDOF needs fewer than COMPASS, M4G or NDOF_FMC_OFF. This only removes hard-iron offsets.
- **Profile: 22 bytes, page 0** (p.33–35, p.55):
  - `ACC_OFFSET` 0x55–0x5A: ±500 LSB.
  - `MAG_OFFSET` 0x5B–0x60: ±6400 LSB at 16 LSB/µT.
  - `GYR_OFFSET` 0x61–0x66: ±2000 LSB at 16 LSB/(°/s).
  - `ACC_RADIUS` 0x67–0x68: ±2048.
  - `MAG_RADIUS` 0x69–0x6A: 144–1280, reset 0x01E0.
  - Each group takes effect **only when its last MSB is written** (Z_MSB or RADIUS_MSB).
- **Saving:** read the profile only after full calibration, and only in CONFIGMODE (p.53).
- **Restoring:** switch to CONFIGMODE, write the offsets and radii, then switch to a fusion mode (p.53). Wrong offsets give unreliable data even when the status shows 3.
- **Soft-iron:** `SIC_MATRIX` 0x43–0x54 is a 3×3 matrix of int16 Q14 values (±2.0); the default is the identity (0x4000 on the diagonal). It is applied to mag data before fusion. Producing it is the user's job, ideally with Helmholtz coils (p.52, p.56).

## 9. Interrupts

- **Pin behavior** (p.40):
  - INT fires on a rising edge and stays latched high until `SYS_TRIGGER.RST_INT` (bit6) is set.
  - `INT_EN` 0x10 (page 1) enables a source, and `INT_MSK` 0x0F (page 1) routes it to the pin.
  - `INT_STA` 0x37 (page 0) clears on read.
- **Bit layout**, the same in all three registers (p.74, p.91–92): 7 ACC_NM, 6 ACC_AM, 5 ACC_HIGH_G, 4 GYR_DRDY, 3 GYR_HIGH_RATE, 2 GYRO_AM, 1 MAG_DRDY, 0 ACC_BSX_DRDY.
- **Data-ready** requires **firmware ≥ 03.14** (p.40, p.56 fn.6).
  - In fusion modes, ACC_BSX_DRDY fires on every fused-data update.
  - In non-fusion modes, each sensor's DRDY follows that sensor's own rate.
  - If INT_STA is not read, the pin pulses low then high on each new event (p.41).

| Interrupt | Threshold LSB (by range) | Timing | Ref |
|---|---|---|---|
| Acc any-motion `ACC_AM_THRES` 0x11 | 3.91 / 7.81 / 15.63 / 31.25 mg (2/4/8/16 g) | slope over Δt = 1/(2·BW); fires after AM_DUR+1 consecutive samples above threshold | p.43–45, p.92–93 |
| Acc slow/no-motion `ACC_NM_THRES` 0x15, `ACC_NM_SET` 0x16 | same as any-motion | no-motion delay in s: dur[5:4]=00 → d+1; 01 → d·4+20; dur[5]=1 → d·8+88 (1 s tick) | p.42–43, p.94 |
| Acc high-g `ACC_HG_THRES` 0x14 | 7.81 / 15.63 / 31.25 / 62.5 mg | (n+1)·2 ms, from 2 to 512 ms | p.45, p.93 |
| Gyro high-rate `GYR_HR_*_SET` 0x18/0x1A/0x1C | 62.5 °/s at the 2000 °/s range, halving with each range step | (n+1)·2.5 ms, from 2.5 to 640 ms; plus hysteresis | p.46–47, p.95–97 |
| Gyro any-motion `GYR_AM_THRES` 0x1E | 1 °/s at the 2000 °/s range | fires after (samples+1)·4 consecutive samples | p.48–49, p.97–98 |

Axis enables: `ACC_INT_Settings` 0x12 (p.93) and `GYR_INT_SETTING` 0x17 (p.95).

## 10. Self-test, status and IDs

- **POST at boot:** `ST_RESULT` 0x36 bits 3–0 = MCU, GYR, MAG, ACC, with 1 meaning pass. Expect **0x0F** (p.50, p.73).
- **BIST:** in CONFIGMODE, set `SYS_TRIGGER` bit0 and wait 400 ms (p.50). `SYS_ERR` 0 means pass and 3 means fail; on a failure, `ST_RESULT` shows which sensor.
- **`SYS_STATUS` 0x39** (p.74):
  - 0 idle; 1 error; 2 initializing peripherals; 3 system initialization; 4 self-test.
  - 5 **fusion running**; 6 running without fusion.
- **`SYS_ERR` 0x3A**, valid when status = 1 (p.75):
  - 1 peripheral init failed; 2 system init failed; 3 self-test failed.
  - 4 register value out of range; 5 register address out of range; 6 register write error.
  - 7 low-power mode not available for this operating mode; 8 accel power mode not available.
  - 9 fusion configuration error; 0xA sensor configuration error.
- **IDs** (p.58, p.60):
  - `CHIP_ID` 0x00 = **0xA0**.
  - Sensor IDs: ACC 0xFB, MAG 0x32, GYR 0x0F.
  - Revisions: `SW_REV_ID` 0x04/0x05, bootloader 0x06.
  - `UNIQUE_ID`: page 1, 0x50–0x5F.
- **Register pages:** `PAGE_ID` 0x07 exists on both pages. Page 0 holds data, system and calibration registers; page 1 holds sensor configuration and interrupts (p.55). Reserved bits should be masked (p.54).

## 11. Interfaces and clock

- **Protocol select:** PS1/PS0 = 00 I²C, 01 HID-I²C, 10 UART. The pins **must not float** (p.99).
- **I²C** (p.100–102):
  - 7-bit addressing, standard or fast mode (≤ 400 kHz). The chip **uses clock stretching**.
  - Address **0x29 when COM3 is high**: COM3 has an internal 20–60 kΩ pull-up, so a floating pin gives 0x29.
  - Address **0x28 when COM3 is low**; HID mode uses 0x40.
  - The register address auto-increments. A read starts at the last address written.
  - Allow 2 µs idle between writes in normal mode and **450 µs** in suspend or LP1.
  - A START followed immediately by a STOP is not supported.
- **UART** (p.103): 115200 baud, 8N1, at most 128 bytes per transfer.
  - Write: `AA 00 reg len data…`. The reply is `EE status`, where 0x01 means success.
  - Read: `AA 01 reg len`. The reply is `BB len data…`, or `EE err` on failure.
  - Characters must arrive within 30 ms of each other. An invalid start byte is dropped silently.
- **Clock** (p.110–111):
  - The internal oscillator is the default and can drift **up to ±3 %**. Bosch recommends an external 32 kHz crystal with 22 pF load caps.
  - Switch in CONFIGMODE by setting `SYS_TRIGGER.CLK_SEL` (bit7); the switch takes about 600 ms.
  - Poll `SYS_CLK_STATUS.ST_MAIN_CLK` (0x38, bit0) until it reads 0, then check that CLK_SEL is still 1. The chip clears it if the crystal is faulty.

## 12. Startup procedure (synthesized from the sections above)

1. Power up with VDD no later than VDDIO, then wait ≥ 400 ms (≥ 650 ms after a reset) (p.14, p.19).
2. Poll `CHIP_ID` until it reads 0xA0. Check `ST_RESULT` = 0x0F, and read `SW_REV_ID` to know whether DRDY is supported.
3. Set `OPR_MODE` to CONFIGMODE and wait 19 ms. Set `PWR_MODE` to normal and `PAGE_ID` to 0.
4. Optional: switch to the external crystal (§11).
5. Write `UNIT_SEL`, `AXIS_MAP_CONFIG` and `AXIS_MAP_SIGN`. On page 1, set the interrupts (and the sensor configuration only for non-fusion modes).
6. If a calibration profile is stored, write its 22 bytes (0x55–0x6A) (§8).
7. Set `OPR_MODE` to NDOF and wait 7 ms. Confirm `SYS_STATUS` = 5.
8. At runtime:
   - Burst-read 0x08–0x34 at ≤ 100 Hz.
   - Watch `CALIB_STAT`. Once every field reads 3, enter CONFIGMODE, read and store the profile, then return to NDOF.

## 13. Datasheet errata and inconsistencies

| # | Issue | Ref |
|---|---|---|
| 1 | Data-ready needs firmware ≥ 03.14, but the stated pre-programmed firmware is 3.11. Read `SW_REV_ID` before relying on DRDY. | p.40 vs p.58 fn.7–8 |
| 2 | The data-rate tolerance is given as ±1 %, but the internal clock deviation as up to ±3 %. | p.14 vs p.111 |
| 3 | The `ACC_Config` field table says BW is <4:3> and range is <2:0>. The bit diagram and Table 3-8 say <4:2> and <1:0>; trust those. | p.87 vs p.29 |
| 4 | `MAG_OFFSET_X_MSB` is printed as "0x56C". The correct address is 0x5C. | p.7, p.83 vs p.55 |
| 5 | `GYR_HR_Y_SET` and `GYR_HR_Z_SET` are marked read-only while X is read/write. This is almost certainly a typo. | p.96–97 vs p.95 |
| 6 | The radius register descriptions repeat the text for "Gyroscope Offset Z". | p.86 |
| 7 | The unit table lists linear accel and gravity in m/s² only, but their representation tables also list mg. | p.32 vs p.38 |
| 8 | The gyro any-motion status is said to be stored "in the INT_EN register". It is actually in INT_STA. | p.49 vs p.74 |
| 9 | The gyro any-motion figure uses both Δt = 1/(4·fs) and 1/(2·bw). | p.48 |

## 14. Cross-check against the `bno_dma` firmware

Snapshot: `NAV_BOX_tofNlnd` at commit `de35563` (2026-10-16). Files are `Core/Src/bno055.c` and `Core/Src/main.c` under `NAV_BOX_tofNlnd/bno_dma/bno_dma/`.

**Consistent with the datasheet:**
- A 45-byte burst DMA read of 0x08–0x34 (`bno055.c:121`) gives one consistent sample (p.39).
- The scale factors (100, 16, 900, 2¹⁴) and the Euler order heading/roll/pitch (`bno055.c:150`) are correct.
- Mode switches wait 24 ms, which is ≥ 19 ms. The post-reset wait is 800 ms, which is ≥ 650 ms.

**Deviations and bugs:**

| # | Finding | Location | Datasheet |
|---|---|---|---|
| 1 | **Bug:** `bno055_acc_conf`, `gyr_conf` and `mag_conf` select page 1, then call `bno055_set_opmode`, which switches back to page 0. The config byte therefore lands on read-only data registers 0x08–0x0B on page 0 and is silently ignored. These functions are not called today, and fusion modes ignore sensor configuration anyway. | `bno055.c:91`, `:101`, `:111` | p.28, p.55 |
| 2 | `bno055_set_unit` writes bit7 = 0, which selects the **Windows** orientation format instead of the Android reset default. This flips the pitch sign convention, and the choice is not documented. | `bno055.c:79` | p.32, p.75 |
| 3 | There is no calibration handling: `CALIB_STAT` is never read and no profile is saved or restored. The calibration motions are needed after every power-up. | — | p.51–53 |
| 4 | `ST_RESULT`, `SYS_STATUS` and `SYS_ERR` are never checked. | — | p.50, p.74–75 |
| 5 | `SYS_TRIGGER = 0x00` (internal clock) is written after `set_pwr_mode` has already returned the chip to NDOF. Bosch recommends clock selection only in CONFIGMODE. | `bno055.c:66` | p.110 |
| 6 | The firmware uses address 0x28 (`BNO_ADDR_ALT`), so the board must tie COM3 low. Floating gives 0x29. | `main.c:109` | p.99–100 |
| 7 | No axis remap is applied, so output stays in the package frame. | — | p.26 |
| 8 | DMA reads restart as soon as each one completes (about 1 ms at 400 kHz), against 100 Hz fusion data. Consumers see each sample about 10 times with no new-sample flag. | `main.c:118`, `:132` | p.33 |
