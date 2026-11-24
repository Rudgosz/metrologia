from machine import Pin
import math
import select
import sys
import time

# --- parametry ---
RELAY_PINS = [18, 19, 20, 10]   # b0 (LSB, 16k), b1, b2, b3 (MSB)
MIN_STEP_MS = 20
SINE_POINTS = 32                # liczba próbek na okres sinusa

N_BITS = len(RELAY_PINS)
MAX_CODE = (1 << N_BITS) - 1

relays = [Pin(p, Pin.OUT) for p in RELAY_PINS]
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
buffer = ""
current_code = 0
step_ms = 300
wave = None
n = 0
next_step = 0

up = list(range(MAX_CODE + 1))
sine = [int(MAX_CODE / 2 * (1 + math.sin(2 * math.pi * k / SINE_POINTS)) + 0.5)
        for k in range(SINE_POINTS)]

WAVES = {
    'u': ("licznik w górę", up),
    'd': ("licznik w dół", list(range(MAX_CODE, -1, -1))),
    's': ("sinus", sine),
    'p': ("prostokąt", [0, MAX_CODE]),
    'b': ("pojedynczy bit", [1 << b for b in range(N_BITS)] + [0]),
    'c': ("przeniesienie 7 <-> 8", [MAX_CODE // 2, MAX_CODE // 2 + 1]),
}


def _set_code(code):
    global current_code
    current_code = max(0, min(MAX_CODE, code))
    for bit, relay in enumerate(relays):
        relay.value((current_code >> bit) & 1)


def _show(label):
    bits = "".join(str((current_code >> b) & 1) for b in range(N_BITS - 1, -1, -1))
    bar = "■" * current_code + "□" * (MAX_CODE - current_code)
    print(f"{label:<22} [{bar}]  {bits} = {current_code}")


def _read_line():
    global buffer
    while poller.poll(0):
        char = sys.stdin.read(1)
        if char not in "\r\n":
            buffer += char
            continue
        line, buffer = buffer.strip().lower(), ""
        if line:
            return line
    return ""


def _set_manual(code):
    global wave
    wave = None
    _set_code(code)
    _show("ręcznie")


def _start(name, codes):
    global wave, n, next_step
    wave = (name, codes)
    n = 0
    next_step = time.ticks_ms()
    print(f"{name}, krok {step_ms} ms")


def _stop():
    global wave
    wave = None
    _set_code(0)
    print("Przebieg zatrzymany.")


def _step():
    global n, next_step
    name, codes = wave
    _set_code(codes[n % len(codes)])
    _show(name)
    n += 1
    next_step = time.ticks_add(time.ticks_ms(), step_ms)


def _execute(cmd):
    global step_ms
    if cmd.isdigit() and int(cmd) <= MAX_CODE:
        _set_manual(int(cmd))
    elif not cmd.strip('+='):
        _set_manual(current_code + len(cmd))
    elif not cmd.strip('-'):
        _set_manual(current_code - len(cmd))
    elif cmd in WAVES:
        _start(*WAVES[cmd])
    elif cmd == 'o' and wave:
        _stop()
    elif cmd.startswith('ms ') and cmd[3:].strip().isdigit():
        step_ms = max(MIN_STEP_MS, int(cmd[3:].strip()))
        print(f"Krok = {step_ms} ms")
    elif cmd == 'h' and wave:
        _stop()
        _help()
    elif cmd == 'h':
        _help()
    else:
        print("Nieznana komenda, 'h' = pomoc.")


def _help():
    print("============== HELP ==============")
    print("Ręcznie:")
    print(f"  0..{MAX_CODE:<6} ustaw kod")
    print("  + / =     kod +1 (np. +++ lub ===)")
    print("  -         kod -1 (np. ---)")
    print("Przebiegi:")
    print("  u         licznik w górę")
    print("  d         licznik w dół")
    print("  s         sinus")
    print("  p         prostokąt")
    print("  b         pojedynczy bit")
    print("  c         przeniesienie 7 <-> 8")
    print("Inne:")
    print("  o         stop")
    print(f"  ms 200    długość kroku (min {MIN_STEP_MS} ms)")
    print("  h         pomoc")


_set_code(0)
_help()

while True:
    cmd = _read_line()
    if cmd:
        _execute(cmd)
    if wave and time.ticks_diff(time.ticks_ms(), next_step) >= 0:
        _step()
    time.sleep_ms(5)
