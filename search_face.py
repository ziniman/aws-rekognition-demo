#!/usr/bin/python

# start your camera using photobooth for a preview and to warm up the camera before running this script

import numpy as np
import cv2
import boto3
import os
from sys import argv
from botocore.exceptions import BotoCoreError, ClientError
import json
from time import sleep
from random import randint

import contextlib
import sys

class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

@contextlib.contextmanager
def ignore_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

region = 'eu-west-1' # change this to switch to another AWS region
colors = [ ['green', 100,240,100], ['red', 0,0,255], ['purple', 255,0,255], ['blue', 255,0,0], ['silver', 192,192,192], ['cyan', 0,255,255], ['orange', 255,99,71], ['white', 255,255,255], ['black', 0,0,0] ]

reko = boto3.client('rekognition', region_name=region)

# Take a photo with USB webcam
# Set save to True if you want to save the image (in the current working directory)
# and open Preview to see the image
def take_photo(save=False):
    sleep(2)
    with ignore_stderr():
    # change the number of the camera that you open to cycle through different options if you have multiple connected cameras
        cam = cv2.VideoCapture(1)
        sleep(2)
        cv2.namedWindow("Preview", cv2.WINDOW_NORMAL)
        #cv2.namedWindow("Preview")

    img_counter = 0
    flag = True
    while flag:
        ret, frame = cam.read()
        cv2.imshow("Preview", frame)
        if not ret:
            break
        k = cv2.waitKey(1)

        if k%256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            break
        elif k%256 == 32:
            # SPACE pressed
            #img_name = "opencv_frame_{}.png".format(img_counter)
            retval, image = cam.retrieve()
            flag = False
    cam.release()
    cv2.destroyAllWindows()
    small = cv2.resize(image, (0,0), fx=0.60, fy=0.60)
    if save:
        cv2.imwrite('image.png', small)
    #    os.system('open -a Preview image.png')
    retval, encoded_image = cv2.imencode('.png',small)
    encoded_image_bytes = encoded_image.tobytes()
    return encoded_image_bytes

# Read image from file
def read_image(filename):
    try:
        fin = open(filename, 'r')
        encoded_image_bytes = fin.read()
        fin.close()
        return encoded_image_bytes
    except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
            exit(-1)

# rekognition facial detection
def reko_detect_faces(image_bytes):
    print "Calling Amazon Rekognition: detect_faces"
    response = reko.detect_faces(
        Image={
            'Bytes': image_bytes
        }
    )
    #print json.dumps(response, sort_keys=True, indent=4)
    return response

def reko_search_faces(image_bytes, collection_id):
    print "Calling Amazon Rekognition: search_faces_by_image"
    try:
        response = reko.search_faces_by_image(
            CollectionId=collection_id,
            Image={
                'Bytes': image_bytes
            },
            FaceMatchThreshold=70,
            MaxFaces=1
        )
        #print json.dumps(response, sort_keys=True, indent=4)
        return response
    except:
        print ("SearchFace error")
        return False

def search_faces(encoded_image, reko_response, collection_id):
    encoded_image=np.fromstring(encoded_image,np.uint8);
    image = cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
    image_height, image_width = image.shape[:2]
    new_image = image
    i = 0
    for mydict in reko_response['FaceDetails']:
        # Find bounding box for this face
        height = mydict['BoundingBox']['Height']
        left = mydict['BoundingBox']['Left']
        top = mydict['BoundingBox']['Top']
        width = mydict['BoundingBox']['Width']
        #crop face to new image
        width_pixels = 80 if int(width * image_width)<80 else int(width * image_width)
        height_pixels = 80  if int(height * image_height)<80 else int(height * image_height)
        left_pixel = int(left * image_width)
        top_pixel = int(top * image_height)

        crop_img = image[top_pixel-20:top_pixel+height_pixels+20, left_pixel-20:left_pixel+width_pixels+20]
        cv2.imwrite('%d.png' % (i), crop_img)
        retval, encoded_image = cv2.imencode('.png',crop_img)
        encoded_image_bytes = encoded_image.tobytes()
        face_matches = reko_search_faces(encoded_image_bytes, collection_id)
        # draw this bounding box
        if face_matches:
            title = "No Match"
            for myfaces in face_matches['FaceMatches']:
                if myfaces:
                    # Find bounding box for this face
                    name = myfaces['Face']['ExternalImageId']
                    confidence = myfaces['Similarity']
                    print ("Face detaced: " + name)
                    title = '%.2f%% - %s' % (confidence, name.title())
            # draw this bounding box
            if i >= len(colors):
                c = randint(0, len(colors)-1)
            else:
                c = i
            new_image = draw_bounding_box(new_image, image_width, image_height, width, height, top, left, colors[c], title, i)
        i += 1
        if i == 5: break
    # write the image to a file
    cv2.imwrite('face_bounding_boxes.jpg', new_image)
    os.system('open -a Preview face_bounding_boxes.jpg')

# draw bounding boxe around one face
def draw_bounding_box(cv_img, cv_img_width, cv_img_height, width, height, top, left, color, title, i):
    # calculate bounding box coordinates top-left - x,y, bottom-right - x,y
    width_pixels = int(width * cv_img_width)
    height_pixels = int(height * cv_img_height)
    left_pixel = 0 if left<0 else int(left * cv_img_width)
    top_pixel = 0 if top<0 else int(top * cv_img_height)
    cv2.rectangle(cv_img,(left_pixel, top_pixel),(left_pixel+width_pixels, top_pixel+height_pixels),(color[1],color[2],color[3]),2)
    font = cv2.FONT_HERSHEY_SIMPLEX

    if (i % 2) == 0:
        text_location = top_pixel + height_pixels + 25
    else:
        text_location = top_pixel - 10

    cv2.putText(cv_img, title, (left_pixel, text_location), font, 0.7, (color[1],color[2],color[3]), 2)
    return cv_img


## START MAIN

# if no arguments take a photo
# if one argument open the image file and decode it
# if more than on argument exit gracefully and print usage guidance
if len(argv) == 1:
    encoded_image = take_photo(save=True)
elif len(argv) == 2:
    print "opening image in file: ", argv[1]
    encoded_image=read_image(argv[1])
else:
    print "Use with no arguments to take a photo with the camera, or one argument to use a saved image"
    exit(-1)

collection_id = "ziniman"
#collection_id = "visa"

humans = reko_detect_faces(encoded_image)

if humans:
    search_faces(encoded_image, humans, collection_id)

else:
    print "No humans detected. Skipping facial search"
