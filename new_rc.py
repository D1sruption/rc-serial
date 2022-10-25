import threading
import keyboard
import time


def main_loop():
    while True:
        if keyboard.read_key() == 'F6':
            print("Detected F6 Key!")


if __name__ == "__main__":
    toggle1 = 0
    toggle2 = 1

    thread = threading.Thread(target=main_loop, daemon=True)
    thread.start()
    time.sleep(1)

