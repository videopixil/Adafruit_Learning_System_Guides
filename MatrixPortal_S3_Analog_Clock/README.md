# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MatrixPortal S3 Analog Clock

An analog clock for the Adafruit MatrixPortal S3 with a 32x32 RGB LED
matrix panel. The clock displays hour and minute hands over a gradient
background that shifts through four color palettes across the day.
Designed for use with a diffuser panel for a soft, blurred aesthetic
inspired by LED artwork behind thick resin.

## Hardware

- [Adafruit MatrixPortal S3](https://www.adafruit.com/product/5778)
- [32x32 RGB LED Matrix - 4mm Pitch (PID 607)](https://www.adafruit.com/product/607)
- LED matrix diffuser panel (optional, recommended)
- USB-C power supply

No Address E jumper is needed for the 32x32 panel.

## CircuitPython Libraries

Install the following from the
[CircuitPython Library Bundle](https://circuitpython.org/libraries)
into the `/lib` folder on your CIRCUITPY drive:

- `adafruit_ntp.mpy`
- `adafruit_connection_manager.mpy`
- `adafruit_requests.mpy`

These are only required for WiFi/NTP mode. The clock also runs in
offline manual mode without them.

## Installation

1. Install [CircuitPython](https://circuitpython.org/board/adafruit_matrixportal_s3/)
   on the MatrixPortal S3
2. Copy the required libraries to `/lib` on the CIRCUITPY drive
3. Copy `settings.toml` and `code.py` to the root of the CIRCUITPY drive
4. Edit `settings.toml` with your WiFi credentials and IANA timezone
   string (e.g. `America/New_York`, `Europe/London`, `Asia/Tokyo`)
   — see http://worldtimeapi.org/timezones for the full list

## Usage

### Boot Modes

**WiFi mode** — If valid WiFi credentials are in `settings.toml`, the
clock connects to WiFi, syncs time via NTP, and starts the clock
automatically. Time re-syncs every hour.

**Offline mode** — If no WiFi credentials are found or the connection
fails, the display shows a message and enters a manual time-set screen:

- **UP button** increments the blinking value (hours, then minutes)
- **DOWN button** confirms and moves to the next field

### Controls (Clock Running)

- **UP button** — Toggle wave animation speed (calm / fast)
- **DOWN button** — Cycle background palettes (morning → day → evening →
  night → auto)

### Time Periods

The background gradient changes automatically based on the time of day:

| Period  | Hours       | Gradient                        | Hand Color |
|---------|-------------|---------------------------------|------------|
| Morning | 6 AM–12 PM  | Purple → Gold → Olive Green     | Cyan       |
| Day     | 12 PM–5 PM  | Blue → Pale Blue → Sandy Tan    | Orange     |
| Evening | 5 PM–8 PM   | Teal → Salmon → Periwinkle      | Yellow-Green |
| Night   | 8 PM–6 AM   | Pink → Purple → Blue            | Yellow     |

Color palettes are inspired by the Florida Arts License Plate.

### Daylight Saving Time

The clock automatically handles DST by querying
[worldtimeapi.org](http://worldtimeapi.org) at boot. Set `TIMEZONE` in
`settings.toml` to your IANA timezone string (e.g. `America/New_York`)
and the correct UTC offset — including any DST adjustment — is fetched
automatically. If the API is unreachable, the clock falls back to the
static `TZ_OFFSET` value.

### Features

- Animated wave effect on the background gradient
- Radial glow vignette (brighter center, dimmer edges)
- Soft glow halo around clock hands
- Twinkling yellow stars during nighttime mode
- Plus-shaped hour markers at each 5-minute position
- NTP time sync with offline fallback
- Manual time set for use without WiFi

## Customization

Key values to adjust at the top of `code.py`:

- `WAVE_SPEED` / `WAVE_SPEED_FAST` — Animation speeds
- `WAVE_AMP` — Wave intensity (row displacement)
- `GRAD_*` — Background gradient color stops per period
- `HAND_*` — Hand colors per period
- `MARKER_*` — Hour marker colors per period
- `MORNING_HOUR`, `DAY_HOUR`, `EVENING_HOUR`, `NIGHT_HOUR` — Period
  boundaries (24-hour format)
- `BG_MULTS` — Radial glow brightness tiers
- `GLOW_RADIUS` — How far the center glow extends
- `STARS` — Star positions and twinkle phase offsets
