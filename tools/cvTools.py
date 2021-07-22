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

def find_intersection(x1,y1,x2,y2,x3,y3,x4,y4):
    if ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) == 0:
        return False
    px= ( (x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) 
    py= ( (x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) )
    return px, py

def bounding_box(points):
    x_coordinates, y_coordinates = zip(*points)

    return [(min(x_coordinates), min(y_coordinates)), (max(x_coordinates), max(y_coordinates))]