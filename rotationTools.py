import cv2
import numpy as np
import math
from cvTools import *

def _pre_process(img, verbosity=0, debug=0):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = 255-img
    img = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
            cv2.THRESH_BINARY,31,1) # cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,21,4
    if debug > 1:
        show(img, "thresh")

    kernel = np.ones((4, 4), np.uint8) # Modify this for adjusting how much it can cover up holes
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=1)
    if debug > 1:
        show(img, "open")
    return img

def smart_rotate(img, verbosity=0, debug=0):
    processedimg = _pre_process(img.copy(), debug=debug)

    lines = cv2.HoughLinesP(processedimg,1,np.pi/2,1000, 1, minLineLength=800,maxLineGap=15)
    
    try:
        if lines == None:
            if verbosity > 0:
                print("No horizontal lines could be found to align perspective. Double check image for defects")
            return np.array([])
    except:
        pass

    if debug > 0:
        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(processedimg, (x1, y1), (x2, y2), color=(100, 100, 100), thickness=1)
        show(processedimg)

    slopes = get_slopes(lines)
    radian_slopes = [abs(math.atan(slope)) for slope in slopes]
    avg_slope = np.median(radian_slopes)
    if verbosity > 1:
        print("Average slope in radians:", avg_slope)

    rot = 0
    if avg_slope > np.pi/4:
        rot = 1
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if verbosity > 1:
            print('rotated')
    return rot, img

if __name__ == '__main__':
    path = "../data/warp_images/input/0100_2021-06-11-00-15-45.jpg"
    img = cv2.imread(path)
    img = smart_rotate(img)
    show(img)