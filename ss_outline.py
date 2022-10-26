import cv2
import numpy as np
import win32api
from mss import mss, tools

# ortakare = int(input("fov...: "))
ortakare = int(500)

# lower = np.array([140,111,160])
# upper = np.array([148,154,194])

lower = np.array([140,110,150])
upper = np.array([150,195,255])

# Change this for what level to aim at
# + is DOWN
# - is UP
# -25 is about chest level
# -40 is about head level
y_axis_adjustment = -40
head_adjustment = -40
chest_adjustment = -25



sct = mss()

boyutlar = sct.monitors[1]
boyutlar['left'] = int((boyutlar['width'] / 2) - (ortakare / 2))
boyutlar['top'] = int((boyutlar['height'] / 2) - (ortakare / 2))
boyutlar['width'] = ortakare
boyutlar['height'] = ortakare
mid = ortakare/2

# img = cv2.imread('./test_image_1.png', cv2.IMREAD_UNCHANGED)
img = np.array(sct.grab(boyutlar))

img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(img_hsv, lower, upper)
kernel = np.ones((3,3), np.uint8)
dilated = cv2.dilate(mask, kernel, iterations=4)

thresh_img = cv2.threshold(dilated, 50, 255, cv2.THRESH_BINARY)[1]
#ret,thresh_img = cv2.threshold(img_grey, thresh, 255, cv2.THRESH_BINARY)
contours, hierarchy = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
print(f"Num Contours: {len(contours)}")
if len(contours) != 0:
    M = cv2.moments(thresh_img)
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])
    x = -(mid - cX) if cX < mid else cX - mid
    y = -(mid - cY) if cY < mid else cY - mid

    cY_head = cY + head_adjustment
    cY_chest = cY + chest_adjustment

    # Center
    cv2.circle(img, (cX, cY), 5, (255, 0, 0), -5)
    cv2.putText(img, "center", (cX + 30, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)

    # Head
    cv2.circle(img, (cX, cY_head), 5, (0, 255, 0), -1)
    cv2.putText(img, "head", (cX + 30, cY_head), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    # Chest
    cv2.circle(img, (cX, cY_chest), 5, (0, 255, 0), -1)
    cv2.putText(img, "chest", (cX + 30, cY_chest), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    # Point Test
    for c in contours:
        cv2.drawContours(thresh_img, [c], -1, (36, 255, 12), 1)
        result1 = cv2.pointPolygonTest(c, (cX, cY_chest), False)
        result2 = cv2.pointPolygonTest(c, (cX, cY_head), False)
        result3 = cv2.pointPolygonTest(c, (cX, cY), False)

    print(f"Chest: {'True' if result1 > 0 else 'False'}")
    print(f"Head: {'True' if result2 > 0 else 'False'}")
    print(f"Center: {'True' if result3 > 0 else 'False'}")

    cv2.imwrite('./thresh.png', img)
    cv2.imwrite('./output.png', thresh_img)
    # print(cX, cY, x, y)

else:
    print(f"No contours!")
    cv2.imwrite('./thresh.png', img)
