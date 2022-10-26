import os
import signal
import threading
import keyboard
import time
from serial import Serial
from struct import pack, unpack


SERIAL_DEVICE = 'COM3'
BAUD_RATE = 115200
serial = Serial(SERIAL_DEVICE, BAUD_RATE)

# Mouse bitwise operators
MOUSE_LEFT = 1
MOUSE_RIGHT = 2
MOUSE_UP = 16
MOUSE_DOWN = 8

# Threading events for mouse states
left_mouse_down_event = threading.Event()

# Cheese Status
CheeseEnabled = threading.Event()
RecoilState = threading.Event()


def recoil_loop():
    while serial.is_open:
        RecoilState.wait()

        i = 0
        while serial.is_open and RecoilState.is_set():
            if i % 2 == 0:
                # this is the speed. lower '10' to increase speed. increase '10' to decrease speed
                # perhaps can make this based on active gun? ie phantom shoots faster so need to pull down faster...
                time.sleep(5/1000)
            else:
                # FIRST: X-axis (POSITIVE = move right, NEGATIVE = move left)
                # SECOND: Y-axis (POSITIVE = move down, NEGATIVE = move up)
                # THIRD: unknown...something to do with mouse wheel
                serial.write(pack('bbb', 1, 6, -1))
            i += 1


def state_loop():
    enabled = False
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'f7':
            print(f"Aborting!")
            os.kill(os.getpid(), signal.SIGINT)
        if event.event_type == keyboard.KEY_DOWN and event.name == 'f6':
            if not enabled:
                enabled = not enabled
                CheeseEnabled.set()
                print(f"Cheese: ENABLED")
                time.sleep(.5)
            else:
                enabled = not enabled
                CheeseEnabled.clear()
                print(f"Cheese: DISABLED")
                time.sleep(.5)


def main_loop():
    print(f"Starting main loop...")

    while serial.is_open:
        # BUTTONS: 1 = left mouse button
        #          2 = right mouse button
        #          4 = middle mouse button
        #          16 = X1 (Most forward button)
        #          8  = X2 (Most rearward button)
        # DX: (x/y coordinate system)
        #          -1 = mouse moving LEFT
        #           1 = mouse moving RIGHT
        # DY: (x/y coordinate system)
        #           -1 = mouse moving UP
        #            1 = mouse moving DOWN
        # WHEEL:
        #            1 = mouse wheel UP
        #           -1 = mouse wheel DOWN
        buttons, dx, dy, wheel, wheel_horizontal = unpack('bbbbb', serial.read(5))

        # print(buttons, dx, dy, wheel, wheel_horizontal)

        left_mouse_state = buttons & MOUSE_LEFT

        if CheeseEnabled.is_set():
            if not left_mouse_down_event.is_set() and left_mouse_state:
                print("applying recoil reduction...", end="", flush=True)
                RecoilState.set()
                left_mouse_down_event.set()
            elif left_mouse_down_event.is_set() and not left_mouse_state:
                print(" done")
                RecoilState.clear()
                left_mouse_down_event.clear()


if __name__ == "__main__":
    thread1 = threading.Thread(target=state_loop)
    thread2 = threading.Thread(target=main_loop)
    thread3 = threading.Thread(target=recoil_loop)
    thread1.start()
    thread2.start()
    thread3.start()
    time.sleep(1)

    thread1.join()
    thread2.join()
    thread3.join()




