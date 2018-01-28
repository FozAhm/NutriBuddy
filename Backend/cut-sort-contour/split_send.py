import NutriBuddyRequest
import cv2
import sys
# Python script that takes an input with 4 photos :
# python split_send.py C:\\Users\\alien\\Downloads\\27536889_1348932631879392_115959185_o.jpg


first_arg = sys.argv[1]

def splitsend(path = first_arg):  #path to be properly escaped (\\)
    #load and cut image:
    #import file, change path there.
    img = cv2.imread(path, 1) # 1 BGR, 0 grayscale, -1 alpha    
    height, width = img.shape[:2]
    im1= img[0:height/2, 0:width/2]  #top left
    cv2.imwrite("tmp\\im1.jpg",im1)
    im2= img[height/2:height, 0:width/2] #bottom left
    cv2.imwrite("tmp\\im2.jpg",im2)
    im3 = img[0:height/2, width/2:width] #top right
    cv2.imwrite("tmp\\im3.jpg",im3)
    im4= img[height/2:height, width/2:width] #bottom right
    cv2.imwrite("tmp\\im4.jpg",im4)

    #sends images to 4 different instances of watson
    file = open('API_keys.txt',"r")
    contents = file.readlines()
    i = 1
    for line in contents:
        elements = line.split(",")
        path = "tmp\\im" + str(i) + ".jpg"   
        NutriBuddyRequest.watsonRequest(path, elements[0],elements[1])
        i = i +1
    print("success")

if __name__ == '__main__':
    # Map command line arguments to function arguments.
    splitsend()
