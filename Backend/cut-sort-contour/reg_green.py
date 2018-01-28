import cv2
import numpy

def red(path, type):  #path to be properly escaped (\\), bool = 1 for green contour, 0 for red contour

    #import file
    img = cv2.imread(path, 1) # 1 BGR, 0 grayscale, -1 alpha

    #convert to inary (needed for contours)
    imgray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    #threshold for contour detection: to be adjusted depending on brightness
    _,thresh = cv2.threshold(imgray,90,255,cv2.THRESH_BINARY_INV) #second number: sensitivity: higher, more contours.

    #contour generation on top of original image:
    _, contours, _ = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, contours, -1, (0,0,255), 20) #red
    
    cv2.imwrite("drawable\\" + type + ".jpg" ,img)

def green(path, type):  #path to be properly escaped (\\), bool = 1 for green contour, 0 for red contour

    #import file
    img = cv2.imread(path, 1) # 1 BGR, 0 grayscale, -1 alpha

    #convert to inary (needed for contours)
    imgray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    #threshold for contour detection: to be adjusted depending on brightness
    _,thresh = cv2.threshold(imgray,90,255,cv2.THRESH_BINARY_INV) #second number: sensitivity: higher, more contours.

    #contour generation on top of original image:
    _, contours, _ = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, contours, -1, (0,255,0), 30) #green
    
    cv2.imwrite("drawable\\" + type + ".jpg" ,img)