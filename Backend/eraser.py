import cv2
import numpy
import sys

first_arg = sys.argv[1]

def erase(path = first_arg):  #path to be properly escaped (\\)

  #import file
  img = cv2.imread(path, ) # 1 BGR, 0 grayscale, -1 alpha

  #convert to binary (needed for contours)
  imgray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

  #threshold for contour detection: to be adjusted depending on brightness
  ret,thresh = cv2.threshold(imgray,80,255,cv2.THRESH_BINARY_INV) #second number: sensitivity: higher, more contours.

  #contour generation:
  image, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

  #creating black image to transfer the most outer contour to:
  bw_image = numpy.ones(imgray.shape, imgray.dtype)
  cv2.drawContours(bw_image, contours, -1, (255),5)

  #fill in white:
  cv2.fillPoly(bw_image, contours, (255) , lineType=8, shift=0)

  #mask to overlay on original image:
  tmp = cv2.cvtColor(bw_image, cv2.COLOR_GRAY2BGR)
  final = cv2.bitwise_or(img, tmp)

  cv2.imwrite(path,final)

if __name__ == '__main__':
    # Map command line arguments to function arguments.
    erase()