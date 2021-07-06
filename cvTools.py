import cv2

def show(img, name="img"):
    """Displays image until keypress"""
    cv2.imshow(name, img)
    cv2.waitKey(0)
    cv2.destroyWindow(name)

def get_slope(x1, y1, x2, y2):
    if x2-x1 == 0:
        return 1000
    return (y2-y1)/(x2-x1)

def get_slopes(lines):
    slopes = []
    for line in lines:
        for x1, y1, x2, y2 in line:
            slopes.append(get_slope(x1, y1, x2, y2))
    return slopes