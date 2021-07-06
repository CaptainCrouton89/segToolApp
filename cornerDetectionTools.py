import cv2
import numpy as np
import jenkspy as jp
import math
from cvTools import *

colors = {"RED": (255, 0, 0), "GREEN": (0, 255, 0), "BLUE": (0, 0, 255), "YELLOW": (255, 255, 0), "CYAN": (0, 255, 255), "MAGENTA": (255, 0, 255)}

def cluster_points(points, nclusters):
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    compactness, _, centers = cv2.kmeans(points, nclusters, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    return compactness, centers

def find_intersection(x1,y1,x2,y2,x3,y3,x4,y4):
        if ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) == 0:
            return False
        px= ( (x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) 
        py= ( (x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) )
        return px, py

def segment_lines(lines):
    slopes = get_slopes(lines)
    radian_slopes = [math.atan(slope) for slope in slopes]
    # Perform a jenks natural breaks segmentation of data
    # This separates our slopes into the four sides of the quadrilateral
    min_s1, max_s1, max_s2, max_s3, max_s4 = jp.jenks_breaks(radian_slopes, nb_class=4)
    all_lines = [[], [], [], []]
    all_rad_slopes = [[], [], [], []]
    for line in lines:
        for x1, y1, x2, y2 in line:
            rad_slope = math.atan(get_slope(x1, y1, x2, y2))
            if rad_slope <= max_s1:
                all_lines[0].append(line)
                all_rad_slopes[0].append(rad_slope)
            elif rad_slope <= max_s2:
                all_lines[1].append(line)
                all_rad_slopes[1].append(rad_slope)
            elif rad_slope <= max_s3:
                all_lines[2].append(line)
                all_rad_slopes[2].append(rad_slope)
            elif rad_slope <= max_s4:
                all_lines[3].append(line)
                all_rad_slopes[3].append(rad_slope)
    # Sometimes, only 3 slopes really exist, but it'll break one segment of slopes into a subset. This should be recombined with similar sloped ones
    # Test if few number, and VERY similar slope

    slopes = [np.mean(rad_slopes) for rad_slopes in all_rad_slopes]

    all_lines_p = []
    slopes_p = []
    for lines, ms1 in zip(all_lines, slopes):
        matches = False
        for i, ms2 in enumerate(slopes_p):
            if abs(ms1) > np.pi/2 - .08 and ms1 + ms2 < .08:
                all_lines_p[i].extend(lines)
                matches = True
            elif abs(ms1 - ms2) < .08 or abs(ms2 - ms1) < .08:
                all_lines_p[i].extend(lines)
                matches = True
            else:
                pass
        if not matches:
            slopes_p.append(ms1)
            all_lines_p.append(lines)

    all_lines_p = [line for line in all_lines_p if len(line) > 2]    
    return all_lines_p

def get_intersections_of_linesets(lines1, lines2):
        Px = []
        Py = []
        for line1 in lines1:
            for line2 in lines2:                    
                x1, y1, x2, y2 = line1[0]
                x3, y3, x4, y4 = line2[0]
                i_pt = find_intersection(float(x1), float(y1), float(x2), float(y2), float(x3), float(y3), float(x4), float(y4))
                if i_pt:
                    Px.append(i_pt[0])
                    Py.append(i_pt[1])
        return Px, Py

def _pre_process(img):
    """Filters image for easy outlining"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = 255-gray
    blur = cv2.blur(gray, (10, 10))
    ret,thresh = cv2.threshold(blur, 240, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((50,50), np.uint8) # Modify this for adjusting how much it can cover up holes
    morph = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    rect = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel)
    return rect

def find_corners(img, verbosity=0, debug=0):
    """ Finds corners of solar panel image
    
    Done by filtering image, finding edges, using houghtransforms to find 
    line approximations, segmenting all lines into four groups (representing each edge of the 
    solar panel), finding the intersections between each group of lines, and then using a clustering
    algorithm to find the "average" point in each cluster, representing the best approximation of 
    each corner.

    Args:
        img: 
            Image of solar panel

    Returns
        A list containing the four corners of the image in the format [[x, y], [x, y], etc]
    """
    height, width, channels = img.shape
    original = img.copy()
    img = _pre_process(img)
    edges = cv2.Canny(img,50,150,apertureSize = 3)
    edges = cv2.dilate(edges, np.ones((10, 10), dtype=np.uint8))
    lines = cv2.HoughLinesP(edges,2,np.pi/360,100, 1, minLineLength=700,maxLineGap=200)

    contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    
    all_lines = segment_lines(lines)

    if debug > 0:
        houghimg = original.copy()
        for i, line_set in enumerate(all_lines):
            for line in line_set:
                for x1, y1, x2, y2 in line:
                    cv2.line(houghimg, (x1, y1), (x2, y2), color=list(colors.values())[i], thickness=5)
        show(houghimg, "lines")

    # find the line intersection points
    point_list = []
    for i, line_set1 in enumerate(all_lines):
        for line_set2 in all_lines[i+1:]:
            point_list.append(get_intersections_of_linesets(line_set1, line_set2))

    Px = []
    Py = []
    margin = 50
    for x_list, y_list in point_list:
        for x, y in zip(x_list, y_list):
            if x < -margin or x > width + margin or y < -margin or y > height + margin:
                continue
            else:
                Px.append(max(0, min(x, width)))
                Py.append(max(0, min(y, height)))

    if debug > 0:
        intersectsimg = houghimg.copy()
        for cx, cy in zip(Px, Py):
            cx = np.round(cx).astype(int)
            cy = np.round(cy).astype(int)
            color = np.random.randint(0,255,3).tolist()
            cv2.circle(intersectsimg, (cx, cy), radius=10, color=color, thickness=-1)
        show(intersectsimg, "centers")

    P = np.float32(np.column_stack((Px, Py)))
    compactness, centers = cluster_points(P, 4)
    
    if compactness > 10000000:
        if len(contours) == 0:
            if verbosity > 0:
                print("No edges found")
            return np.array([])
        max_contour = max(contours, key = cv2.contourArea)
        reduced_centers = []
        _, centers_5 = cluster_points(P, 5)
        centers_5 = [[int(c[0]), int(c[1])] for c in centers_5]
        for c in centers_5:
            if abs(cv2.pointPolygonTest(max_contour, (c[0],c[1]), True)) < 100:
                reduced_centers.append(c)
        if len(reduced_centers) != 4:
            if verbosity > 0:
                print("Found more than 4 edge intersections. Check image for artifacts")
            return np.array([])
        centers = reduced_centers

    if debug > 0:
        for cx, cy in centers:
            cx = np.round(cx).astype(int)
            cy = np.round(cy).astype(int)
            cv2.circle(original, (cx, cy), radius=10, color=[150, 150, 150], thickness=-1) # -1: filled circle
        show(original, "centers")

    centers = [[int(c[0]), int(c[1])] for c in centers]

   # Test if any two corners are too close together for the image to be a "pass"
    proximity_threshold = 600
    for x1, y1 in centers:
        for x2, y2 in centers:
            if x1 != x2 or y1 != y2:
                if (x1-x2)**2 + (y1-y2)**2 < proximity_threshold:
                    if verbosity > 0:
                        print("Clipped corners/edges on image")
                    return np.array([])
    return np.array(centers)
