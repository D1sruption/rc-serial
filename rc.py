from serial import Serial
from struct import pack, unpack
from threading import Thread, Event
from datetime import datetime, timedelta
from random import randint
from time import sleep
import keyboard
 
SERIAL_DEVICE='COM3'
BAUD_RATE=115200
 
MIN_SLEEP=10
MAX_SLEEP=15

# This adjust Y axis power
RECOIL_CORRECTION_Y_MIN=1
RECOIL_CORRECTION_Y_MAX=4

# This adjust X axis power
RECOIL_CORRECTION_X_MIN=1
RECOIL_CORRECTION_X_MAX=4
 
MOUSE_LEFT=1
MOUSE_RIGHT=2
MOUSE_UP=16
MOUSE_DOWN=8
 
serial = Serial('COM3', 115200)
left_mouse_down_event = Event()
 
def loop():
    print("Starting...")
    while serial.is_open:
        #print("Serial open!")
        left_mouse_down_event.wait()
 
        i = 0
        if keyboard.is_pressed('f6'):
            print("F6 Pressed!")
        while serial.is_open and left_mouse_down_event.is_set():
            if i % 2 == 0:
                sleep(randint(MIN_SLEEP, MAX_SLEEP)/1000)
            else:
                #serial.write(pack('bbb', randint(RECOIL_CORRECTION_X_MIN, RECOIL_CORRECTION_X_MAX), randint(RECOIL_CORRECTION_Y_MIN, RECOIL_CORRECTION_Y_MAX), -1))
                serial.write(pack('bbb', 0, 5, -1))
            i += 1
 
thread = Thread(target=loop)
thread.start()
 
try:
    #print("In try")
    enabled = False
    previous_up_mouse_state = False
 
    while serial.is_open:
        #print("Try serial open")
        buttons, dx, dy, wheel, wheel_horizontal = unpack('bbbbb', serial.read(5))
 
        left_mouse_state = buttons & MOUSE_LEFT
        up_mouse_state = buttons & MOUSE_UP
        #print(buttons, dx, dy, wheel, wheel_horizontal)
 
        if up_mouse_state != previous_up_mouse_state:
            #print("abc1")
            if up_mouse_state:
               # print("abc2")
                enabled = not enabled
                print(f"recoil reduction: {'yes' if enabled else 'no'}")
            previous_up_mouse_state = up_mouse_state
 
        if enabled:
            #print("Enabled!")
            if wheel < 0:
                MAX_SLEEP = max(5, MAX_SLEEP-1)
                MIN_SLEEP = max(1, MIN_SLEEP-1)
            elif wheel > 0:
                MAX_SLEEP = MAX_SLEEP+1
                MIN_SLEEP = MIN_SLEEP+1
 
            if wheel != 0:
                print(f"recoil sleep: ({MIN_SLEEP}, {MAX_SLEEP})")
 
            if not left_mouse_down_event.is_set() and left_mouse_state:
                print("applying recoil reduction...", end="", flush=True)
                left_mouse_down_event.set()
            elif left_mouse_down_event.is_set() and not left_mouse_state:
                print(" done")
                left_mouse_down_event.clear()
    #print("End of try!")
 
except:
    print("Exception!")
    serial.close()
    left_mouse_down_event.set()
    thread.join()