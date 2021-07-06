import cv2
import numpy as np

source = np.float32([[0, 0], [100, 0], [100, 100], [0, 100]])
dest = np.float32([[0, 0], [-1000, 0], [-1000, -1000], [0, -1000]])

points = np.float32([[[50, 50]]])

homography, _ = cv2.findHomography(source, dest)

transformed = cv2.perspectiveTransform(points, homography)

print(transformed)
# => [[[-500. -500.]]]

homography_inverse = np.linalg.inv(homography)

detransformed = cv2.perspectiveTransform(transformed, homography_inverse)

print(detransformed)
# => [[[50. 50.]]]