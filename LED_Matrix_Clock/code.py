# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

'''LED Matrix Alarm Clock with Scrolling Wake Up Text and Winking Eyes'''
import os
import ssl
import time
import random
import wifi
import socketpool
import microcontroller
import board
import audiocore
import audiobusio
import audiobusio
import audiomixer
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_rgbmatrixqt import Adafruit_RGBMatrixQT
import adafruit_ntp
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from rainbowio import colorwheel
from adafruit_seesaw import digitalio, rotaryio, seesaw
from adafruit_debouncer import Button

timezone = -4 # your timezone offset
alarm_hour = 14 # hour is 24 hour for alarm to denote am/pm
alarm_min = 54 # minutes
alarm_volume = .2 # float 0.0 to 1.0
hour_12 = True # 12 hour or 24 hour time
no_alarm_plz = False
BRIGHTNESS_DAY = 200 # led brightness during day (7am-7:59pm)
BRIGHTNESS_NIGHT = 50 # led brightness during night (8pm-6:59am)

# I2S pins for Audio BFF
DATA = board.A0
LRCLK = board.A1
BCLK = board.A2

# connect to WIFI
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=timezone, cache_seconds=3600)

# Initialize I2C
i2c = board.STEMMA_I2C()

# Initialize both matrix displays
matrix1 = Adafruit_RGBMatrixQT(i2c, address=0x30, allocate=adafruit_is31fl3741.PREFER_BUFFER)
matrix2 = Adafruit_RGBMatrixQT(i2c, address=0x31, allocate=adafruit_is31fl3741.PREFER_BUFFER)
matrix1.global_current = 0x05
matrix2.global_current = 0x05
# Start with day brightness
current_brightness = BRIGHTNESS_DAY
matrix1.set_led_scaling(current_brightness)
matrix2.set_led_scaling(current_brightness)
matrix1.enable = True
matrix2.enable = True
matrix1.fill(0x000000)
matrix2.fill(0x000000)
matrix1.show()
matrix2.show()

audio = audiobusio.I2SOut(BCLK, LRCLK, DATA)
wavs = []
for filename in os.listdir('/'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/"+filename)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)
mixer.voice[0].level = alarm_volume
wav_filename = wavs[random.randint(0, (len(wavs))-1)]
wav_file = open(wav_filename, "rb")
audio.play(mixer)

def open_audio():
    n = wavs[random.randint(0, (len(wavs))-1)]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return w

def get_brightness_for_time(hour_24):
    """Get appropriate brightness based on 24-hour time"""
    # Night time: 8pm (20:00) to 6:59am (06:59) - brightness 50
    # Day time: 7am (07:00) to 7:59pm (19:59) - brightness 200
    if hour_24 >= 20 or hour_24 < 7:
        return BRIGHTNESS_NIGHT
    else:
        return BRIGHTNESS_DAY

def update_brightness(hour_24):
    """Update LED brightness based on time of day"""
    global current_brightness
    new_brightness = get_brightness_for_time(hour_24)

    if new_brightness != current_brightness:
        current_brightness = new_brightness
        matrix1.set_led_scaling(current_brightness)
        matrix2.set_led_scaling(current_brightness)
        print(f"Brightness updated to {current_brightness} for hour {hour_24}")

seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ss_pin = digitalio.DigitalIO(seesaw, 24)
button = Button(ss_pin, long_duration_ms=1000)

button_held = False
encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

# Simple 5x7 font bitmap patterns for digits 0-9 and letters
FONT_5X7 = {
    '0': [
        0b01110,
        0b10001,
        0b10011,
        0b10101,
        0b11001,
        0b10001,
        0b01110
    ],
    '1': [
        0b00100,
        0b01100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b01110
    ],
    '2': [
        0b01110,
        0b10001,
        0b00001,
        0b00010,
        0b00100,
        0b01000,
        0b11111
    ],
    '3': [
        0b11111,
        0b00010,
        0b00100,
        0b00010,
        0b00001,
        0b10001,
        0b01110
    ],
    '4': [
        0b00010,
        0b00110,
        0b01010,
        0b10010,
        0b11111,
        0b00010,
        0b00010
    ],
    '5': [
        0b11111,
        0b10000,
        0b11110,
        0b00001,
        0b00001,
        0b10001,
        0b01110
    ],
    '6': [
        0b00110,
        0b01000,
        0b10000,
        0b11110,
        0b10001,
        0b10001,
        0b01110
    ],
    '7': [
        0b11111,
        0b00001,
        0b00010,
        0b00100,
        0b01000,
        0b01000,
        0b01000
    ],
    '8': [
        0b01110,
        0b10001,
        0b10001,
        0b01110,
        0b10001,
        0b10001,
        0b01110
    ],
    '9': [
        0b01110,
        0b10001,
        0b10001,
        0b01111,
        0b00001,
        0b00010,
        0b01100
    ],
    ' ': [
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000
    ],
    'W': [
        0b10001,
        0b10001,
        0b10001,
        0b10101,
        0b10101,
        0b11011,
        0b10001
    ],
    'A': [
        0b01110,
        0b10001,
        0b10001,
        0b11111,
        0b10001,
        0b10001,
        0b10001
    ],
    'K': [
        0b10001,
        0b10010,
        0b10100,
        0b11000,
        0b10100,
        0b10010,
        0b10001
    ],
    'E': [
        0b11111,
        0b10000,
        0b10000,
        0b11110,
        0b10000,
        0b10000,
        0b11111
    ],
    'U': [
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b01110
    ],
    'P': [
        0b11110,
        0b10001,
        0b10001,
        0b11110,
        0b10000,
        0b10000,
        0b10000
    ],
    'O': [
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b01110
    ],
    'N': [
        0b10001,
        0b11001,
        0b10101,
        0b10101,
        0b10011,
        0b10001,
        0b10001
    ],
    'F': [
        0b11111,
        0b10000,
        0b10000,
        0b11110,
        0b10000,
        0b10000,
        0b10000
    ]
}

# Eye animation patterns with eyelashes
EYE_OPEN = [
    0b10101,  # Eyelashes - scattered pattern above eye
    0b01110,  # Eye outline top
    0b10001,  # Eye sides
    0b10101,  # Eye with pupil
    0b10001,  # Eye sides
    0b01110,  # Eye outline bottom
    0b00000
]

EYE_CLOSED = [
    0b00000,
    0b00000,
    0b00000,
    0b11111,
    0b00000,
    0b00000,
    0b00000
]

def draw_pixel_flipped(matrix, x, y, color):
    """Draw a pixel with 180-degree rotation"""
    flipped_x = 12 - x
    flipped_y = 8 - y
    if 0 <= flipped_x < 13 and 0 <= flipped_y < 9:
        matrix.pixel(flipped_x, flipped_y, color)

def draw_char(matrix, char, x, y, color):
    """Draw a character at position x,y on the specified matrix (flipped)"""
    if char.upper() in FONT_5X7:
        bitmap = FONT_5X7[char.upper()]
        for row in range(7):
            for col in range(5):
                if bitmap[row] & (1 << (4 - col)):
                    draw_pixel_flipped(matrix, x + col, y + row, color)

def draw_eye(matrix, x, y, eye_pattern, color):
    """Draw an eye pattern at position x,y on the specified matrix"""
    for row in range(7):
        for col in range(5):
            if eye_pattern[row] & (1 << (4 - col)):
                draw_pixel_flipped(matrix, x + col, y + row, color)

def draw_winking_eyes(color, wink_state=0):
    """Draw eyes on both matrices with winking animation
    wink_state: 0=both open, 1=left wink, 2=right wink, 3=both closed"""
    # Clear both displays
    matrix1.fill(0x000000)
    matrix2.fill(0x000000)

    # Position eyes in center of each matrix
    eye_x = 4  # Center horizontally (13-5)/2 = 4
    eye_y = 1  # Center vertically

    # Draw left eye on matrix1
    if wink_state == 1 or wink_state == 3:
        draw_eye(matrix1, eye_x, eye_y, EYE_CLOSED, color)
    else:
        draw_eye(matrix1, eye_x, eye_y, EYE_OPEN, color)

    # Draw right eye on matrix2
    if wink_state == 2 or wink_state == 3:
        draw_eye(matrix2, eye_x, eye_y, EYE_CLOSED, color)
    else:
        draw_eye(matrix2, eye_x, eye_y, EYE_OPEN, color)

    # Update both displays
    matrix1.show()
    matrix2.show()

def perform_wink_animation(color):
    """Perform the complete winking animation sequence"""
    # Animation sequence: open -> left wink -> open -> right wink -> open
    wink_sequence = [0, 1, 0, 2, 0]

    for wink_state in wink_sequence:
        draw_winking_eyes(color, wink_state)
        time.sleep(0.3)  # Hold each frame for 300ms

def draw_colon_split(y, color, is_pm=False):
    """Draw a split colon with 2x2 dots between the displays, with optional PM indicator"""
    # Top dot - left half on matrix1, right half on matrix2
    draw_pixel_flipped(matrix1, 12, y+1, color)  # Top-left
    draw_pixel_flipped(matrix1, 12, y + 2, color)  # Bottom-left
    draw_pixel_flipped(matrix2, 0, y+1, color)   # Top-right
    draw_pixel_flipped(matrix2, 0, y + 2, color)   # Bottom-right

    # Bottom dot - left half on matrix1, right half on matrix2
    draw_pixel_flipped(matrix1, 12, y + 4, color)  # Top-left
    draw_pixel_flipped(matrix1, 12, y + 5, color)  # Bottom-left
    draw_pixel_flipped(matrix2, 0, y + 4, color)   # Top-right
    draw_pixel_flipped(matrix2, 0, y + 5, color)   # Bottom-right

    # Add third dot for PM indicator (positioned below the colon)
    if is_pm:
        draw_pixel_flipped(matrix1, 12, y + 6, color)  # Left half
        draw_pixel_flipped(matrix2, 0, y + 6, color)   # Right half

def draw_text(text, color=0xFFFFFF, is_pm=False):
    """Draw text across both matrices with proper spacing"""
    # Clear both displays
    matrix1.fill(0x000000)
    matrix2.fill(0x000000)

    # For "12:00" layout with spacing:
    # "1" at x=0 on matrix1 (5 pixels wide)
    # "2" at x=6 on matrix1 (5 pixels wide, leaving 1-2 pixels space before colon)
    # ":" split between matrix1 and matrix2
    # "0" at x=2 on matrix2 (leaving 1-2 pixels space after colon)
    # "0" at x=8 on matrix2 (5 pixels wide)

    y = 1  # Vertical position

    # Draw first two digits on matrix1
    if len(text) >= 2:
        draw_char(matrix1, text[0], 0, y, color)   # First digit at x=0
        draw_char(matrix1, text[1], 6, y, color)   # Second digit at x=6 (leaves space for colon)

    # Draw the colon split between displays
    if len(text) >= 3 and text[2] == ':':
        draw_colon_split(y, color, is_pm)

    # Draw last two digits on matrix2
    if len(text) >= 5:
        draw_char(matrix2, text[3], 2, y, color)   # Third digit at x=2 (leaves space after colon)
        draw_char(matrix2, text[4], 8, y, color)   # Fourth digit at x=8

    # Update both displays
    matrix1.show()
    matrix2.show()
    print("updated matrices")

def draw_scrolling_text(text, offset, color=0xFFFFFF):
    """Draw scrolling text across both matrices"""
    # Clear both displays
    matrix1.fill(0x000000)
    matrix2.fill(0x000000)

    # Total width available: 26 pixels (13 per matrix)
    total_width = 26
    char_width = 6  # 5 pixels for character + 1 pixel spacing
    text_width = len(text) * char_width

    y = 1  # Vertical position

    # Calculate starting position for scrolling
    start_x = total_width - offset

    for i, char in enumerate(text):
        char_x = start_x + (i * char_width)

        # Determine which matrix to draw on
        if char_x >= -5 and char_x < 13:  # Character visible on matrix1
            if char_x >= 0:
                draw_char(matrix1, char, char_x, y, color)
            else:
                # Character partially visible on matrix1
                draw_char(matrix1, char, char_x, y, color)
        elif char_x >= 8 and char_x < 26:  # Character visible on matrix2
            matrix2_x = char_x - 13
            if matrix2_x >= 0:
                draw_char(matrix2, char, matrix2_x, y, color)
            else:
                # Character spans both matrices
                draw_char(matrix2, char, matrix2_x, y, color)

    # Update both displays
    matrix1.show()
    matrix2.show()

def blink_animation(text, color, is_pm=False, blink_count=3, blink_duration=200):
    """Perform a blink animation for entering alarm setting mode"""
    for _ in range(blink_count):
        # Turn off display
        matrix1.fill(0x000000)
        matrix2.fill(0x000000)
        matrix1.show()
        matrix2.show()
        time.sleep(blink_duration / 1000.0)

        # Turn on display with text
        draw_text(text, color, is_pm)
        time.sleep(blink_duration / 1000.0)

refresh_clock = ticks_ms()
refresh_timer = 3600 * 1000
clock_clock = ticks_ms()
clock_timer = 1000
# Add blink timer for alarm setting mode
alarm_blink_clock = ticks_ms()
alarm_blink_timer = 500  # 500ms blink interval
alarm_blink_state = True
# Add scrolling timer for alarm mode
scroll_clock = ticks_ms()
scroll_timer = 80  # 150ms scroll interval
scroll_offset = 0
# Add winking timer
wink_clock = ticks_ms()
wink_timer = 30000  # 30 seconds in milliseconds
# Add alarm status display variables
alarm_status_scroll_clock = ticks_ms()
alarm_status_scroll_timer = 100  # 100ms scroll interval for status
alarm_status_scroll_offset = 0
showing_alarm_status = False
alarm_status_duration = 3000  # Show status for 3 seconds
alarm_status_start_time = ticks_ms()
# Add auto-silence variables
alarm_start_time = ticks_ms()
alarm_auto_silence_duration = 60000  # 1 minute in milliseconds

first_run = True
new_time = False
color_value = 0
COLOR = colorwheel(0)
# Add variables for PM tracking
is_pm = False
alarm_is_pm = False
time_str = "00:00"
set_alarm = 0
active_alarm = False
alarm = f"{alarm_hour:02}:{alarm_min:02}"

while True:

    button.update()
    if button.long_press:
        # long press to set alarm & turn off alarm
        if set_alarm == 0 and not active_alarm:
            set_alarm = 1
            # Calculate alarm display format and PM status for 12-hour mode
            if hour_12:
                alarm_display_hour = alarm_hour % 12
                if alarm_display_hour == 0:
                    alarm_display_hour = 12
                alarm_is_pm = alarm_hour >= 12
                alarm_text = f"{alarm_display_hour:02}:  "
            else:
                alarm_text = f"{alarm_hour:02}:  "
                alarm_is_pm = False
            # Perform blink animation when entering alarm setting mode
            blink_animation(alarm_text, COLOR, alarm_is_pm)
            draw_text(alarm_text, COLOR, alarm_is_pm)
        if active_alarm:
            mixer.voice[0].stop()
            active_alarm = False
            # Restore normal brightness based on current time
            update_brightness(am_pm_hour)
            scroll_offset = 0  # Reset scroll position
            print("Alarm manually silenced")
    if button.short_count == 1:
        # short press to set hour and minute
        set_alarm = (set_alarm + 1) % 3
        if set_alarm == 0:
            draw_text(time_str, COLOR, is_pm)
        elif set_alarm == 2:
            # Perform blink animation when entering minute setting mode
            blink_animation(f"  :{alarm_min:02}", COLOR, alarm_is_pm)
            draw_text(f"  :{alarm_min:02}", COLOR, alarm_is_pm)
    if button.short_count == 3:
        no_alarm_plz = not no_alarm_plz
        print(f"alarms off? {no_alarm_plz}")
        # Start showing alarm status
        showing_alarm_status = True
        alarm_status_start_time = ticks_ms()
        alarm_status_scroll_offset = 0

    position = -encoder.position
    if position != last_position:
        if position > last_position:
            # when setting alarm, rotate through hours/minutes
            # when not, change color for LEDs
            if set_alarm == 0:
                color_value = (color_value + 5) % 255
            elif set_alarm == 1:
                alarm_hour = (alarm_hour + 1) % 24
                # Update PM status when changing hours
                if hour_12:
                    alarm_is_pm = alarm_hour >= 12
            elif set_alarm == 2:
                alarm_min = (alarm_min + 1) % 60
        else:
            if set_alarm == 0:
                color_value = (color_value - 5) % 255
            elif set_alarm == 1:
                alarm_hour = (alarm_hour - 1) % 24
                # Update PM status when changing hours
                if hour_12:
                    alarm_is_pm = alarm_hour >= 12
            elif set_alarm == 2:
                alarm_min = (alarm_min - 1) % 60
        alarm = f"{alarm_hour:02}:{alarm_min:02}"
        COLOR = colorwheel(color_value)
        if set_alarm == 0:
            draw_text(time_str, COLOR, is_pm)
        elif set_alarm == 1:
            # Display hour in 12-hour format when hour_12 is True
            if hour_12:
                display_hour = alarm_hour % 12
                if display_hour == 0:
                    display_hour = 12
                draw_text(f"{display_hour:02}:  ", COLOR, alarm_is_pm)
            else:
                draw_text(f"{alarm_hour:02}:  ", COLOR, False)
        elif set_alarm == 2:
            draw_text(f"  :{alarm_min:02}", COLOR, alarm_is_pm)
        last_position = position

    # Handle alarm status scrolling display
    if showing_alarm_status:
        if ticks_diff(ticks_ms(), alarm_status_scroll_clock) >= alarm_status_scroll_timer:
            # Determine which text to show based on alarm status
            if no_alarm_plz:
                status_text = "OFF "
            else:
                status_text = "ON "
            
            char_width = 6
            text_width = len(status_text) * char_width
            total_width = 26  # Total width of both matrices

            # Scroll the status text
            draw_scrolling_text(status_text, alarm_status_scroll_offset, COLOR)
            alarm_status_scroll_offset += 1

            # Reset scroll when text has completely scrolled off screen
            if alarm_status_scroll_offset > text_width + total_width:
                alarm_status_scroll_offset = 0

            alarm_status_scroll_clock = ticks_add(alarm_status_scroll_clock, alarm_status_scroll_timer)

        # Check if we should stop showing alarm status
        if ticks_diff(ticks_ms(), alarm_status_start_time) >= alarm_status_duration:
            showing_alarm_status = False
            # Return to normal display
            if set_alarm == 0 and not active_alarm:
                draw_text(time_str, COLOR, is_pm)

    # Handle auto-silence of alarm after 1 minute
    if active_alarm and ticks_diff(ticks_ms(), alarm_start_time) >= alarm_auto_silence_duration:
        print("Auto-silencing alarm after 1 minute")
        mixer.voice[0].stop()
        active_alarm = False
        # Restore normal brightness based on current time
        update_brightness(am_pm_hour)
        scroll_offset = 0  # Reset scroll position
        # Note: no_alarm_plz is NOT changed - alarm stays enabled for next day
        draw_text(time_str, COLOR, is_pm)  # Return to time display

    # Handle eye winking animation every 30 seconds (only when showing normal time)
    elif set_alarm == 0 and not active_alarm:
        if ticks_diff(ticks_ms(), wink_clock) >= wink_timer:
            print("Performing wink animation!")
            perform_wink_animation(COLOR)
            # Restore the time display after winking
            draw_text(time_str, COLOR, is_pm)
            wink_clock = ticks_add(wink_clock, wink_timer)

    # Handle scrolling text when alarm is active
    if active_alarm:
        if ticks_diff(ticks_ms(), scroll_clock) >= scroll_timer:
            wake_up_text = "WAKE UP "
            char_width = 6
            text_width = len(wake_up_text) * char_width
            total_width = 26  # Total width of both matrices

            # Scroll the text
            draw_scrolling_text(wake_up_text, scroll_offset, COLOR)
            scroll_offset += 1

            # Reset scroll when text has completely scrolled off screen
            if scroll_offset > text_width + total_width:
                scroll_offset = 0

            scroll_clock = ticks_add(scroll_clock, scroll_timer)

    # Handle blinking in alarm setting mode
    elif set_alarm > 0:
        if ticks_diff(ticks_ms(), alarm_blink_clock) >= alarm_blink_timer:
            alarm_blink_state = not alarm_blink_state
            if alarm_blink_state:
                # Show the alarm setting
                if set_alarm == 1:
                    if hour_12:
                        display_hour = alarm_hour % 12
                        if display_hour == 0:
                            display_hour = 12
                        draw_text(f"{display_hour:02}:  ", COLOR, alarm_is_pm)
                    else:
                        draw_text(f"{alarm_hour:02}:  ", COLOR, False)
                elif set_alarm == 2:
                    draw_text(f"  :{alarm_min:02}", COLOR, alarm_is_pm)
            else:
                # Hide the alarm setting (show blank)
                matrix1.fill(0x000000)
                matrix2.fill(0x000000)
                matrix1.show()
                matrix2.show()
            alarm_blink_clock = ticks_add(alarm_blink_clock, alarm_blink_timer)

    # resync with NTP time server every hour
    if set_alarm == 0:
        if ticks_diff(ticks_ms(), refresh_clock) >= refresh_timer or first_run:
            try:
                print("Getting time from internet!")
                now = ntp.datetime
                print(now)
                total_seconds = time.mktime(now)
                first_run = False
                am_pm_hour = now.tm_hour
                # Update brightness based on current time
                update_brightness(am_pm_hour)
                if hour_12:
                    hours = am_pm_hour % 12
                    if hours == 0:
                        hours = 12
                    is_pm = am_pm_hour >= 12
                else:
                    hours = am_pm_hour
                    is_pm = False
                time_str = f"{hours:02}:{now.tm_min:02}"
                print(time_str)
                mins = now.tm_min
                seconds = now.tm_sec
                if not active_alarm and not showing_alarm_status:  # Only draw time if alarm is not active and not showing status
                    draw_text(time_str, COLOR, is_pm)
                refresh_clock = ticks_add(refresh_clock, refresh_timer)
            except Exception as e: # pylint: disable=broad-except
                print("Some error occured, retrying! -", e)
                time.sleep(10)
                microcontroller.reset()

        # keep time locally between NTP server syncs
        if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
            seconds += 1
            # print(seconds)
            if seconds > 59:
                mins += 1
                seconds = 0
                new_time = True
            if mins > 59:
                am_pm_hour += 1
                mins = 0
                new_time = True
                # Update brightness when hour changes
                update_brightness(am_pm_hour)
            if hour_12:
                hours = am_pm_hour % 12
                if hours == 0:
                    hours = 12
                is_pm = am_pm_hour >= 12
            else:
                hours = am_pm_hour
                is_pm = False
            if new_time:
                time_str = f"{hours:02}:{mins:02}"
                new_time = False
                print(time_str)
                if not active_alarm and not showing_alarm_status:  # Only draw time if alarm is not active and not showing status
                    draw_text(time_str, COLOR, is_pm)
                if f"{am_pm_hour:02}:{mins:02}" == alarm and not no_alarm_plz:
                    print("alarm!")
                    # grab a new wav file from the wavs list
                    wave = open_audio()
                    mixer.voice[0].play(wave, loop=True)
                    active_alarm = True
                    alarm_start_time = ticks_ms()  # Record when alarm started
                    scroll_offset = 0  # Reset scroll position when alarm starts
            clock_clock = ticks_add(clock_clock, clock_timer)
