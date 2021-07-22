import numpy as np
import cv2
import math

# Global variables used to determine clockwise order of points
centroid = [2, 3]
refvec = [0, 1]

def clockwiseangle_and_distance(point):
    vector = [point[0]-centroid[0], point[1]-centroid[1]]
    lenvector = math.hypot(vector[0], vector[1])
    if lenvector == 0:
        return -math.pi, 0
    normalized = [vector[0]/lenvector, vector[1]/lenvector]
    dotprod  = normalized[0]*refvec[0] + normalized[1]*refvec[1]     # x1*x2 + y1*y2
    diffprod = refvec[1]*normalized[0] - refvec[0]*normalized[1]     # x1*y2 - y1*x2
    angle = math.atan2(diffprod, dotprod)
    if angle < 0:
        return 2*math.pi+angle, lenvector
    return angle, lenvector

def set_centroid(cx, cy):
	global centroid
	centroid = [cx, cy]

def order_points(pts):
	if pts.shape[0] == 0:
		return np.asarray([])
	rect = np.zeros((4, 2), dtype = "float32")
	cx = sum([p[0] for p in pts])/len(pts)
	cy = sum([p[1] for p in pts])/len(pts)
	set_centroid(cx, cy)
	pts = np.asarray(pts, dtype = "float32")
	rect = np.asarray(sorted(pts, key=clockwiseangle_and_distance))
	return rect

def four_point_transform(image, pts, verbosity=0, debug=0):
	rect = order_points(pts)
	if rect.shape == 0:
		return np.asarray([]), np.asarray([])
	(tl, tr, br, bl) = rect
	widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
	widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
	maxWidth = max(int(widthA), int(widthB))
	heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
	heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
	maxHeight = max(int(heightA), int(heightB))
	dst = np.array([
		[0, 0],
		[maxWidth - 1, 0],
		[maxWidth - 1, maxHeight - 1],
		[0, maxHeight - 1]], dtype = "float32")
	trans_matrix = cv2.getPerspectiveTransform(rect, dst)
	warped_image = cv2.warpPerspective(image, trans_matrix, (maxWidth, maxHeight))
	return warped_image, trans_matrix