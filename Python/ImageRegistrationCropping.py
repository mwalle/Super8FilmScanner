from __future__ import annotations
from typing import TYPE_CHECKING, List

import cv2 as cv
import numpy as np
import os
import glob
import shutil
import traceback

def OutputFolder() -> str:
    # Create folders for the different EV exposure levels
    
    # Image Output path - create if needed
    path = os.path.join(os.getcwd(), "Aligned")

    if not os.path.exists(path):
        os.mkdir(path)

    return path

def ImageFolder() -> str:
    # Create folders for the different EV exposure levels
    
    # Image Output path - create if needed
    path = os.path.join(os.getcwd(), "Capture")

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    return path

def Filelist(path: str, ext: str) -> int:
    return sorted(glob.glob(os.path.join(path, "frame_????????."+ext)), reverse=False)

# For Details Reference Link:
# http://stackoverflow.com/questions/46036477/drawing-fancy-rectangle-around-face
def draw_border(img, pt1, pt2, color, thickness, r, d):
    x1,y1 = pt1
    x2,y2 = pt2

    # Top left
    cv.line(img, (x1 + r, y1), (x1 + r + d, y1), color, thickness)
    cv.line(img, (x1, y1 + r), (x1, y1 + r + d), color, thickness)
    cv.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)

    # Top right
    cv.line(img, (x2 - r, y1), (x2 - r - d, y1), color, thickness)
    cv.line(img, (x2, y1 + r), (x2, y1 + r + d), color, thickness)
    cv.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)

    # Bottom left
    cv.line(img, (x1 + r, y2), (x1 + r + d, y2), color, thickness)
    cv.line(img, (x1, y2 - r), (x1, y2 - r - d), color, thickness)
    cv.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)

    # Bottom right
    cv.line(img, (x2 - r, y2), (x2 - r - d, y2), color, thickness)
    cv.line(img, (x2, y2 - r), (x2, y2 - r - d), color, thickness)
    cv.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)


def detectSproket(sproket_image):
    # Convert to gray and blur
    matrix = (3, 5)
    sproket_image = cv.GaussianBlur(sproket_image, matrix, 0)
    
    sproket_image = cv.cvtColor(sproket_image, cv.COLOR_BGR2GRAY)

    sproket_image = cv.equalizeHist(sproket_image)
    # Threshold
    _, sproket_image = cv.threshold(sproket_image, 220, 255, cv.THRESH_BINARY)    

    cv.imshow("sproket_image",cv.resize(sproket_image, (0,0), fx=0.5, fy=0.5))

    # Detect the sproket shape
    contours, _ = cv.findContours(sproket_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_TC89_L1)

    #cv.drawContours(image, contours, -1,color=(0,0,255), thickness=cv.FILLED)

    #Abort here if detection found nothing!
    if len(contours)==0:
        return (455, 646), (455, 646),1,1, 0, 1, len(contours)

    # Sort by area, largest first (hopefully our sproket - we should only have 1 full sprocket in view at any 1 time)
    contour = sorted(contours, key=lambda x: cv.contourArea(x), reverse=True)[0]
        

    #colour = (100, 100, 100)
    #cv.drawContours(sproket_image, [contour], -1,color=colour, thickness=cv.FILLED)

    area = cv.contourArea(contour)
    rect = cv.minAreaRect(contour)
    rotation = rect[2]
    centre = rect[0]
    # Gets center of rotated rectangle
    box = cv.boxPoints(rect)
    # Convert dimensions to ints
    box = np.int0(box)

    #print("area",area)
    #print("rotation",rotation)

    a=min(box[0][0],box[1][0],box[2][0],box[3][0])
    b=min(box[0][1],box[1][1],box[2][1],box[3][1])
    top_left_of_sproket_hole=(a,b)

    a=max(box[0][0],box[1][0],box[2][0],box[3][0])
    b=max(box[0][1],box[1][1],box[2][1],box[3][1])
    bottom_right_of_sproket_hole=(a,b)
    #cv.drawContours(sproket_image, [box], -1,color=(200, 0, 0), thickness=2)

    # Check for vertical stretch
    height_of_sproket_hole=bottom_right_of_sproket_hole[1]-top_left_of_sproket_hole[1]
 
    # Check width
    width_of_sproket_hole=bottom_right_of_sproket_hole[0]-top_left_of_sproket_hole[0]

    #print(top_left_of_sproket_hole, bottom_right_of_sproket_hole)
    #cv.rectangle(sproket_image, top_left_of_sproket_hole, bottom_right_of_sproket_hole, 255, 4)

    return top_left_of_sproket_hole, bottom_right_of_sproket_hole,width_of_sproket_hole,height_of_sproket_hole, rotation, area, len(contours)

def cropOriginalImage(image):
    y1=140
    y2=y1+2000
    return image[y1:y2,150:2900].copy()

def scanImageForAverageCalculations(image):
    # Do inital crop of the input image
    # this assumes hardcoded image sizes and will need tweaks depending on input resolution
    image=cropOriginalImage(image)
    h, w =image.shape[:2]

    #Take a vertical strip where the sproket should be (left hand side)
    top_left_of_sproket_hole, bottom_right_of_sproket_hole,width_of_sproket_hole,height_of_sproket_hole, rotation, area, number_of_contours=detectSproket(image[0:h,0:500])

    #Only 1 shape detected, and no rotation
    if number_of_contours==1 and (rotation==0.0 or rotation==90.0):
        cv.rectangle(image, top_left_of_sproket_hole, bottom_right_of_sproket_hole, (0,0,255), 2)
        thumbnail=cv.resize(image, (0,0), fx=0.5, fy=0.5)
        return thumbnail, width_of_sproket_hole,height_of_sproket_hole, area

    return None, None,None,None

def scanImages(files:List, maximum_number_of_samples:int=32):
    # Scan a selection of images looking for "perfect" frames to determine correct
    # size of sproket holes.
    # Asks for human confirmation during the process
    average_sample_count=0
    average_height=0
    average_width=0
    average_area=0

    # Scan first 100 frames/images to determine what "good" looks like
    for filename in files:
        # Quit if we have enough samples
        if average_sample_count>maximum_number_of_samples:
            break

        img = cv.imread(filename,cv.IMREAD_UNCHANGED)
        if img is None:
            print("Error reading",filename)
        else:
            thumbnail, width_of_sproket_hole,height_of_sproket_hole, area=scanImageForAverageCalculations(img)

            if width_of_sproket_hole!=None:
                #Show thumbnail
                
                cv.putText(thumbnail, "Accept frame? y or n", (10, 50), cv.FONT_HERSHEY_SIMPLEX, 1, (250, 0, 250), 2, cv.LINE_AA)
                cv.putText(thumbnail, "w={0} h={1} area={2}".format(width_of_sproket_hole, height_of_sproket_hole, area), (0, 150), cv.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 250), 2, cv.LINE_AA)
                cv.putText(thumbnail, "valid samples={0}".format(average_sample_count), (0, 200), cv.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 250), 2, cv.LINE_AA)
                
                cv.imshow("raw",thumbnail)
                thumbnail=None

                k = cv.waitKey(0) & 0xFF

                if k == ord('y'):
                    cv.destroyWindow("raw")
                    average_sample_count+=1
                    average_height+=height_of_sproket_hole
                    average_width+=width_of_sproket_hole
                    average_area+=area

                if k == 27:
                    return_value = False
                    break
# samples= 16 w= 352 h= 443 area= 151601
    if (average_sample_count<10):
        raise Exception("Unable to detect suitable sample size")

    # Determine averages
    average_height=int(average_height/average_sample_count)
    average_width=int(average_width/average_sample_count)
    average_area=int(average_area/average_sample_count)

    return average_sample_count,average_width,average_height,average_area

def processImage(original_image, output_w,output_h, average_width, average_height, average_area):
    Detect=True
    manual_adjustment=False
    while True:        
        # Do inital crop of the input image
        # this assumes hardcoded image sizes and will need tweaks depending on input resolution
        image=cropOriginalImage(original_image)
        h, w =image.shape[:2]

        if Detect:
            #Take a vertical strip where the sproket should be (left hand side)
            top_left_of_sproket_hole, bottom_right_of_sproket_hole, width_of_sproket_hole, height_of_sproket_hole, rotation, area, number_of_contours=detectSproket(image[0:h,0:500])

        untouched_image=image.copy()

        # draw actual detected sproket hole in grey
        #cv.rectangle(image, top_left_of_sproket_hole, bottom_right_of_sproket_hole, (100,100,100), 3)

        #Draw "average" size rectangle in red, based on detected hole
        tl=(bottom_right_of_sproket_hole[0]-average_width,top_left_of_sproket_hole[1])
        br=(tl[0]+average_width,tl[1]+average_height)
        #Top right
        tr=(br[0],tl[1])
        #cv.rectangle(image, tl, br, (0,0,255), 3)

        draw_border(image,tl,br,(0,0,255),6,50,40)

        #print(top_left_of_sproket_hole, bottom_right_of_sproket_hole,width_of_sproket_hole,height_of_sproket_hole, rotation, area, number_of_contours)

        # Allowable tolerance around the "average"
        padding=20

        # right hand corner of sproket hole seems to be always best aligned (manual observation)
        # so use that as datum for the whole frame capture
        frame_tl=(tr[0]-125,tr[1]-562)
        # Height must be divisble by 2
        frame_br=(frame_tl[0]+output_w,frame_tl[1]+output_h)
        cv.rectangle(image, frame_tl, frame_br, (0,0,0), 20)

        print(tr)

        if frame_tl[1]<0 or frame_tl[0]<0:
            print("frame_tl",frame_tl)
            manual_adjustment=True
        elif number_of_contours>4:
            print("Contours",number_of_contours)
            manual_adjustment=True
        elif height_of_sproket_hole<(average_height-padding) or height_of_sproket_hole>(average_height+padding):
            print("Sproket Height wrong!!",height_of_sproket_hole)
            manual_adjustment=True
        elif width_of_sproket_hole<(average_width-padding) or width_of_sproket_hole>(average_width+padding):
            print("Sproket width wrong!!",width_of_sproket_hole)
            manual_adjustment=True
        #elif top_left_of_sproket_hole[1]<590:
        #    print("top_left_of_sproket_hole Y value low")
        #    manual_adjustment=True
        #elif top_left_of_sproket_hole[0]<80:
        #    print("top_left_of_sproket_hole X value low")
        #    manual_adjustment=True        

        if manual_adjustment==True:
            thumbnail=cv.resize(image, (0,0), fx=0.5, fy=0.5)
            cv.putText(thumbnail, "Cursor keys adjust frame capture, SPACE to confirm", (0, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2, cv.LINE_AA)
            cv.imshow("Adjustment",thumbnail)
            k = cv.waitKeyEx(0) 
            print("key",k)

            # Cursor UP
            if k == 2490368:
                #Move sproket location up
                # change Y coords
                top_left_of_sproket_hole=(top_left_of_sproket_hole[0],top_left_of_sproket_hole[1]-2)
                bottom_right_of_sproket_hole=(bottom_right_of_sproket_hole[0],bottom_right_of_sproket_hole[1]-2)
                Detect=False

            # Down
            if k == 2621440:
                #Move sproket location down
                # change Y coords
                top_left_of_sproket_hole=(top_left_of_sproket_hole[0],top_left_of_sproket_hole[1]+2)
                bottom_right_of_sproket_hole=(bottom_right_of_sproket_hole[0],bottom_right_of_sproket_hole[1]+2)
                Detect=False

            # left
            if k == 2424832:
                #Move sproket location left
                # change X coords
                top_left_of_sproket_hole=(top_left_of_sproket_hole[0]-2,top_left_of_sproket_hole[1])
                bottom_right_of_sproket_hole=(bottom_right_of_sproket_hole[0]-2,bottom_right_of_sproket_hole[1])
                Detect=False

            if k == 2555904:
                #Move sproket location right
                # change X coords
                top_left_of_sproket_hole=(top_left_of_sproket_hole[0]+2,top_left_of_sproket_hole[1])
                bottom_right_of_sproket_hole=(bottom_right_of_sproket_hole[0]+2,bottom_right_of_sproket_hole[1])
                Detect=False

            if k == 27:
                raise Exception("Abort!")

            if k == ord(' '):
                #Accept
                cv.destroyWindow("Adjustment")
                manual_adjustment=False

        if manual_adjustment==False:

            #Black out the sproket hole
            #cv.rectangle(untouched_image,(tr[0]+1,tr[1]-1),(tr[0]-2-average_width,tr[1]+2+average_height),color=(0,0,0),thickness=cv.FILLED)

            if frame_tl[1]<0:
                #Original image is smaller than the crop size/frame size, so pad out
                #Need to pad out the image at the TOP...
                offset_y=abs(frame_tl[1])
                cropped=untouched_image[0:frame_br[1],frame_tl[0]:frame_br[0]].copy()
                h, w =cropped.shape[:2]
                # Full sized image
                output_image = np.zeros((output_h,output_w,3), np.uint8)
                # Place cropped into bottom right corner
                output_image[offset_y:offset_y+h,0:w]=cropped
                return output_image            


            return untouched_image[frame_tl[1]:frame_br[1],frame_tl[0]:frame_br[0]]

    

input_path=ImageFolder()
output_path=OutputFolder()

files=Filelist(input_path,"png")

files=files[469:]

try:
    # Skip this for now, we have already run it!
    #average_sample_count,average_width,average_height,average_area=scanImages(files[:200])

    average_sample_count=33
    average_width=350
    average_height=442
    average_area=150478

    print("samples=",average_sample_count,"w=",average_width,"h=", average_height,"area=", average_area)
    
    previous_output_image=None
    for filename in files:
        new_filename = os.path.join(output_path, os.path.basename(filename))

        img = cv.imread(filename,cv.IMREAD_UNCHANGED)
        if img is None:
            print("Error opening file",filename,"replacing bad frame")
            #Clone frame to cover up corrupt/missing file
            shutil.copy2(previous_output_image, new_filename)
        else:
            print(filename)

            new_image=processImage(img, 2350,1566, average_width, average_height, average_area)

            previous_output_image=new_filename

            if cv.imwrite(new_filename, new_image, [cv.IMWRITE_PNG_COMPRESSION, 1])==False:
                raise IOError("Failed to save image")

            #Show thumbnail at 50% of original
            thumbnail=cv.resize(new_image, (0,0), fx=0.35, fy=0.35)
            cv.imshow("Final",thumbnail)

            k = cv.waitKey(1) & 0xFF

            if k == 27:
                return_value = False
                break

except BaseException as err:
    print(f"Unexpected {err=}")
    traceback.print_exc()
    print("Press any key to shut down")
    cv.waitKey()

finally:
    cv.destroyAllWindows()