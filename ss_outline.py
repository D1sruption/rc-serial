import struct
import time
from random import randint
import cv2
import mss.tools
import numpy as np
import math
import keyboard
import serial
import win32api
import win32con
import win32gui
import win32ui
import os
from serial import Serial
from struct import pack, unpack
import threading
import signal
from termcolor import colored

SERIAL_DEVICE = 'COM3'
BAUD_RATE = 115200
serial = Serial(SERIAL_DEVICE, BAUD_RATE)

# Mouse bitwise operators
MOUSE_LEFT = 1
MOUSE_RIGHT = 2
MOUSE_UP = 16
MOUSE_DOWN = 8

# Cheese Status
CheeseEnabled = threading.Event()
RCSActive = threading.Event()
AimLockState = threading.Event()
WeaponChangeState = threading.Event()
AbortState = threading.Event()
ShootState = threading.Event()
TargetAvailable = threading.Event()

# RCS Variables
RCS_START_DELAY = 230 / 1000 # time.sleep is in seconds so we need to divide by 1000 to get ms
RCS_END_TIME = 1000 / 1000 # Same as above



# Input Status for threading
input_left_mouse = threading.Event()
input_right_mouse = threading.Event()
input_x1_mouse = threading.Event()
input_x2_mouse = threading.Event()
input_mmb_mouse = threading.Event()
input_scrollup_mouse = threading.Event()
input_scrolldown_mouse = threading.Event()
input_shift_kb = threading.Event()


CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.5
COLORS = [(0, 255, 255), (255, 255, 0), (0, 255, 0), (255, 0, 0)]

AIMING_POINT = 0  # 0 for "head", 1 for chest, 2 for legs

# Size of "window" to capture NN on
ACTIVATION_RANGE = 300

DATASET_PATH = f"{os.getcwd()}\yolov5\Valorant_Dataset\data\\"

aim_x, aim_y = 0, 0
MIN_SLEEP=10
MAX_SLEEP=15

SENSITIVITY = .7


def get_keyboard_input():
    enabled = False
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == 'f7':
                #print(f"Aborting!")
                #os.kill(os.getpid(), signal.SIGINT)
                AbortState.set()
            if event.name == 'f6':
                if not enabled:
                    enabled = not enabled
                    CheeseEnabled.set()
                    #print(f"Cheese: {colored('ENABLED', 'green')}")
                    time.sleep(.5)
                else:
                    enabled = not enabled
                    CheeseEnabled.clear()
                    #print(f"Cheese: {colored('DISABLED', 'red')}")
                    time.sleep(.5)
            if event.name == 'shift':
                if not input_shift_kb.is_set():
                    #print(f"WeaponID Toggle: TRUE")
                    input_shift_kb.set()
                    time.sleep(.5)
                elif input_shift_kb.is_set():
                    #print(f"WeaponID Toggle: FALSE")
                    input_shift_kb.clear()
                    time.sleep(.5)
            if event.name == 'f5' and input_shift_kb.is_set():
                if not WeaponChangeState.is_set():
                    #print(f"WeaponChangeState: ACTIVE")
                    WeaponChangeState.set()
                    time.sleep(.5)
                else:
                    #print(f"WeaponChangeState: INACTIVE")
                    WeaponChangeState.clear()
                    time.sleep(.5)


def get_mouse_input():
    global weapon_id
    weapon_id = 0
    while serial.is_open:
        buttons, dx, dy, wheel, wheel_horizontal = unpack('bbbbb', serial.read(5))
        left_mouse_state = buttons & MOUSE_LEFT
        #print(buttons, dx, dy, wheel, wheel_horizontal)

        if not AimLockState.is_set() and left_mouse_state:
            AimLockState.set()
            #print(f"Tx Aimlock")
        elif AimLockState.is_set() and not left_mouse_state:
            AimLockState.clear()
            RCSActive.clear()
            #print(f"done!")

        if AimLockState.is_set() and CheeseEnabled.is_set() and TargetAvailable.is_set():
            RCSActive.set()
            #print(f"Shoosting!")
            #serial.write(pack('bbb', aim_x, aim_y, 0))


        if wheel < 0 and WeaponChangeState.is_set() and not weapon_id <= 0:
            weapon_id = weapon_id - 1
            #print(f"WeaponID: {weapon_id}")
        elif wheel > 0 and WeaponChangeState.is_set() and not weapon_id >= 3:
            weapon_id = weapon_id + 1
            #print(f"WeaponID: {weapon_id}")




def grab_screen(region=None):
    hwin = win32gui.GetDesktopWindow()

    if region:
        left, top, x2, y2 = region
        widthScr = x2 - left + 1
        heightScr = y2 - top + 1
    else:
        widthScr = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        heightScr = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

    hwindc = win32gui.GetWindowDC(hwin)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, widthScr, heightScr)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (widthScr, heightScr), srcdc, (left, top), win32con.SRCCOPY)

    signedIntsArray = bmp.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype='uint8')
    img.shape = (heightScr, widthScr, 4)

    srcdc.DeleteDC()
    memdc.DeleteDC()
    win32gui.ReleaseDC(hwin, hwindc)
    win32gui.DeleteObject(bmp.GetHandle())

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def object_pos():
    global aim_x
    global aim_y
    global SENSITIVITY
    with mss.mss() as sct:
        Wd, Hd = sct.monitors[1]["width"], sct.monitors[1]["height"]

        monitor = (int(Wd / 2 - ACTIVATION_RANGE / 2),
                   int(Hd / 2 - ACTIVATION_RANGE / 2),
                   int(Wd / 2 + ACTIVATION_RANGE / 2),
                   int(Hd / 2 + ACTIVATION_RANGE / 2))

    with open(DATASET_PATH + "coco-dataset.labels", "r") as f:
        class_names = [cname.strip() for cname in f.readlines()]

    net = cv2.dnn.readNet(DATASET_PATH + "yolov4-tiny.weights", DATASET_PATH + "yolov4-tiny.cfg")
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

    model = cv2.dnn_DetectionModel(net)
    model.setInputParams(size=(416, 416), scale=1 / 255, swapRB=True)

    while True:
        start = time.time()

        frame = np.array(grab_screen(region=monitor))
        classes, scores, boxes = model.detect(frame, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)

        for (classID, score, box) in zip(classes, scores, boxes):
            color = COLORS[int(classID) % len(COLORS)]
            label = "%s : %f" % (class_names[classID[0]], score)
            cv2.rectangle(frame, box, color, 2)
            cv2.putText(frame, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        enemyNum = len(boxes)

        if enemyNum == 0:
            #print("No enemies found!")
            pass
        else:
            # Reset distances array to prevent duplicating items
            distances = []
            closest = 1000
            closestObject = None

            # Cycle through results (enemies) and get the closest to the center of detection box
            for i in range(enemyNum):

                X = float(boxes[i][0])
                Y = float(boxes[i][1])
                width = float(boxes[i][2])
                height = float(boxes[i][3])

                # REFERENCE:
                # Center of screen coordinates for 2560x1440 resolution
                # X: 1280 Y: 720

                centerX = X + (width / 2)
                centerY = Y + (height / 2)

                distance = math.sqrt(((centerX - ACTIVATION_RANGE / 2) ** 2) + ((centerY - ACTIVATION_RANGE / 2) ** 2))
                distances.append(distance)

                if distances[i] < closest:
                    closest = distances[i]
                    closestObject = i

            X = float(boxes[closestObject][0])
            Y = float(boxes[closestObject][1])
            width = float(boxes[closestObject][2])
            height = float(boxes[closestObject][3])

            if AIMING_POINT == 0:
                height = (height / 8) * 1

            elif AIMING_POINT == 1:
                height = (height / 8) * 2

            elif AIMING_POINT == 2:
                height = (height / 8) * 5

            cClosestX = X + (width / 2)
            cClosestY = Y + height

            # Image to draw to, Start Pt, End Pt, Color(RGB), thickness
            cv2.line(frame, (int(cClosestX), int(cClosestY)), (int(ACTIVATION_RANGE / 2), int(ACTIVATION_RANGE / 2)),
            (0, 255, 0), 1, cv2.LINE_AA)

            # Modify sensitivity here: < 1 = move slower || > 1 = move faster
            # Documentation:
            # difX is the difference of center of screen to the center point of the object
            # NEGATIVE difX means crosshair is to the RIGHT of the center point of the object
            # POSITIVE difX mean crosshair is to the LEFT of the center point of the object
            # NEGATIVE difY means crosshair is LOWER than the center point of the object
            # POSITIVE difY means crosshair is HIGHER than the center point of the object
            # (0,0) = crosshair is EXACTLY on the center point of the object
            # if we know the exact center pt of our screen is 1280x720 & our
            difX = int(cClosestX - (ACTIVATION_RANGE / 2)) * SENSITIVITY
            difY = int(cClosestY - (ACTIVATION_RANGE / 2)) * SENSITIVITY

            if abs(difX) > 15 or abs(difY) > 15:
                TargetAvailable.clear()
                pass
            else:
                if CheeseEnabled.is_set():
                    #print(f"Rx Aimlockstate!")

                    aim_x = int(float(difX))
                    aim_y = int(float(difY))
                    TargetAvailable.set()
                    i = 0
                    if RCSActive.is_set():
                        serial.write(pack('bbb', int(float(difX)), int(float(difY)), 0))

                # if keyboard.is_pressed('v'):
                #     # data = str(difX) + ':' + str(difY)
                #     # # arduino.write(data.encode())
                #     # print(f"\n\nData: {data.encode()}")
                #     # print(f"cClosestX: {cClosestX} | cClosestY: {cClosestY}")
                #     # print(f"X: {X} | Y: {Y}")
                #     # print(f"Width: {width} | Height: {height}")
                #     # print(f"Activation Range: {(int(ACTIVATION_RANGE / 2), int(ACTIVATION_RANGE / 2))}")
                #     # print(f"CenterX: {centerX} | CenterY: {centerY}")
                #     # print(f"DifX: {difX} | DifY: {difY}")
                #     try:
                #         #serial.write(pack('bbb', int(float(difX)),int(float(difY)), 0))
                #         AimLockState.set()
                #     except (struct.error) as e:
                #         pass



        end = time.time()
        fps_label = "FPS: %.2f" % (1 / (end - start))
        cv2.putText(frame, fps_label, (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            sct.close()
            break


def display_menu():
    while True:
        os.system('cls')
        if CheeseEnabled.is_set():
            print(f"Cheese Status: {colored('ACTIVE', 'green')}", end="\n", flush=True)
            print(f"Mouse Sensitivity: {colored(str(SENSITIVITY), 'blue')}", end="\n\n", flush=True)

            if WeaponChangeState.is_set():
                print(f"WeaponChangeState: {colored('ACTIVE', 'green')}", end=f"   WeaponID: {weapon_id}\n", flush=True)
            elif not WeaponChangeState.is_set():
                print(f"WeaponChangeState: {colored('INACTIVE', 'red')}", end=f"   WeaponID: {weapon_id}\n", flush=True)

            if RCSActive.is_set():
                print(f"RCS State: {colored('ACTIVE', 'green')}", end=f"\n", flush=True)
            elif not RCSActive.is_set():
                print(f"RCS State: {colored('INACTIVE', 'red')}", end="\n", flush=True)

            if AimLockState.is_set():
                print(f"\nAimX/Y: {aim_x}, {aim_y}", end="\n", flush=True)




        elif not CheeseEnabled.is_set():
            print(f"Cheese Status: {colored('INACTIVE', 'red')}", end="\n", flush=True)






        if AbortState.is_set():
            print(f"\n\nAborting!", end="", flush=True)
            os.kill(os.getpid(), signal.SIGINT)

        time.sleep(1)


if __name__ == "__main__":
    thread1 = threading.Thread(target=object_pos)
    thread2 = threading.Thread(target=get_keyboard_input)
    thread3 = threading.Thread(target=get_mouse_input)
    thread4 = threading.Thread(target=display_menu)

    thread1.start()
    thread2.start()
    thread3.start()
    thread4.start()

    time.sleep(1)

    thread1.join()
    thread2.join()
    thread3.join()
    thread4.join()
