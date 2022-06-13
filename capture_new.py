#!/usr/local/bin/python3

# start your camera using photobooth for a preview and to warm up the camera before running this script

import numpy as np
import cv2
import boto3
import os
from sys import argv
from botocore.exceptions import BotoCoreError, ClientError
import json
import pyaudio
import inflect
from time import sleep

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
colors = [ ['green', 0,255,0], ['blue', 255,0,0], ['red', 0,0,255], ['purple', 255,0,255], ['silver', 192,192,192], ['cyan', 0,255,255], ['orange', 255,99,71], ['white', 255,255,255], ['black', 0,0,0] ]

polly = boto3.client("polly", region_name=region)
reko = boto3.client('rekognition', region_name=region)
p = inflect.engine()
pya = pyaudio.PyAudio()

# Take a photo with USB webcam
# Set save to True if you want to save the image (in the current working directory)
# and open Preview to see the image
def take_photo(save=False):
    with ignore_stderr():
           speak("Please point your external camera at the subject")
    sleep(1)
    with ignore_stderr():
        speak("Taking a photo")
    #vidcap=cv2.VideoCapture()
    # change the number of the camera that you open to cycle through different options if you have multiple connected cameras
    cam = cv2.VideoCapture(0)
    #sleep(2)

    cv2.namedWindow("Preview", cv2.WINDOW_NORMAL)

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
            #cv2.imwrite(img_name, frame)
            #print("{} written!".format(img_name))
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
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
            exit(-1)

# Provide a string and an optional voice attribute and play the streamed audio response
# Defaults to the Salli voice
def speak(text_string, voice="Joanna"):
    try:
        # Request speech synthesis
        response = polly.synthesize_speech(Text=text_string,
            TextType="text", OutputFormat="pcm", VoiceId=voice)
    except (BotoCoreError, ClientError) as error:
        # The service returned an error, exit gracefully
        print(error)
        exit(-1)
    # Access the audio stream from the response
    if "AudioStream" in response:
        stream = pya.open(format=pya.get_format_from_width(width=2), channels=1, rate=16000, output=True)
        stream.write(response['AudioStream'].read())
        sleep(1)
        stream.stop_stream()
        stream.close()
    else:
        # The response didn't contain audio data, return False
        print("Could not stream audio")
        return(False)

# Amazon Rekognition label detection
def reko_detect_labels(image_bytes):
    print ("Calling Amazon Rekognition: detect_labels")
#    speak("Detecting labels with Amazon Recognition")
    response = reko.detect_labels(
        Image={
            'Bytes': image_bytes
        },
        MaxLabels=8,
        MinConfidence=60
    )
    return response

# rekognition facial detection
def reko_detect_faces(image_bytes):
    print ("Calling Amazon Rekognition: detect_faces")
    response = reko.detect_faces(
        Image={
            'Bytes': image_bytes
        },
        Attributes=['ALL']
    )
    print (json.dumps(response, sort_keys=True, indent=4))
    return response

# create verbal response describing the detected lables in the response from Rekognition
# there needs to be more than one lable right now, otherwise you'll get a leading 'and'
def create_verbal_response_labels(reko_response):
    mystring = "I detected the following labels: "
    humans = False
    labels = len(reko_response['Labels'])
    if labels == 0:
        mystring = "I cannot detect anything."
    else:
        i = 0
        for mydict in reko_response['Labels']:
            i += 1
            if mydict['Name'] == 'People':
                humans = True
                continue
            print ("%s\t(%.2f)" % (mydict['Name'], mydict['Confidence']))
            if i < labels:
                newstring = "%s, " % (mydict['Name'].lower())
                mystring = mystring + newstring
            else:
                newstring = "and %s. " % (mydict['Name'].lower())
                mystring = mystring + newstring
            if ('Human' in mydict.values()) or ('Person' in mydict.values()) :
                humans = True
    return humans, mystring

def create_verbal_response_face(reko_response):
    mystring = ""

    persons = len(reko_response['FaceDetails'])
    print ("number of persons = ", persons)

    if persons == 1:
        mystring = "I can see one face. "
    else:
        mystring = "I can see %d faces. " % (persons)
    i = 0
    for mydict in reko_response['FaceDetails']:
        # Boolean True|False values for these facial features
        beard = mydict['Beard']['Value']
        eyeglasses = mydict['Eyeglasses']['Value']
        sunglasses = mydict['Sunglasses']['Value']
        mustache = mydict['Mustache']['Value']
        smile = mydict['Smile']['Value']
        if mydict['Gender']['Confidence'] > 60:
            if persons == 1:
                mystring = mystring + "The person is %s. " % (mydict['Gender']['Value'].lower())
            else:
                mystring = mystring + "The %s person is %s. " % (p.number_to_words(p.ordinal(str([i+1]))), mydict['Gender']['Value'].lower())
            if mydict['Gender']['Value'] == 'Male':
                he_she = 'he'
            else:
                he_she = 'she'
        else:
            he_she = 'he'
            if persons == 1:
                mystring = mystring + "This is a person. "
            else:
                mystring = mystring + "The %s person is a human. " % p.number_to_words(p.ordinal(str([i+1])))
        print ("Person %d (%s):" % (i+1, colors[i][0]))
        print ("\tGender: %s\t(%.2f)" % (mydict['Gender']['Value'], mydict['Gender']['Confidence']))
        print ("\tEyeglasses: %s\t(%.2f)" % (eyeglasses, mydict['Eyeglasses']['Confidence']))
        print ("\tSunglasses: %s\t(%.2f)" % (sunglasses, mydict['Sunglasses']['Confidence']))
        print ("\tSmile: %s\t(%.2f)" % (smile, mydict['Smile']['Confidence']))
        if eyeglasses == True and sunglasses == True:
            mystring = mystring + "%s is wearing glasses. " % (he_she.capitalize(), )
        elif eyeglasses == True and sunglasses == False:
            mystring = mystring + "%s is wearing spectacles. " % (he_she.capitalize(), )
        elif eyeglasses == False and sunglasses == True:
            mystring = mystring + "%s is wearing sunglasses. " % (he_she.capitalize(), )
        if smile:
            true_false = 'is'
        else:
            true_false = 'is not'
        mystring = mystring + "%s %s smiling. " % (he_she.capitalize(), true_false)
        print ("\tEmotions:")
        j = 0
        selected_emotion = ''

        mydict['Emotions'].sort(key = my_sort, reverse=True)

        for emotion in mydict['Emotions']:
            print ("\t\t%s\t(%.2f)" % (emotion['Type'], emotion['Confidence']))
            if j == 0 or selected_emotion == '':
                if emotion['Type'].lower() != 'disgusted':
                    mystring = mystring + "%s looks %s. " % (he_she.capitalize(), emotion['Type'].lower())
                    selected_emotion = emotion['Type'].lower()
            j += 1
        # Find bounding box for this face
        height = mydict['BoundingBox']['Height']
        left = mydict['BoundingBox']['Left']
        top = mydict['BoundingBox']['Top']
        width = mydict['BoundingBox']['Width']
        i += 1

        if i > 2:
            break

    return mystring

def my_sort(e):
  return e['Confidence']

def save_image_with_bounding_boxes(encoded_image, reko_response):
    encoded_image=np.fromstring(encoded_image,np.uint8);
    image = cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
    image_height, image_width = image.shape[:2]
    i = 0
    for mydict in reko_response['FaceDetails']:
        # Find bounding box for this face
        height = mydict['BoundingBox']['Height']
        left = mydict['BoundingBox']['Left']
        top = mydict['BoundingBox']['Top']
        width = mydict['BoundingBox']['Width']
        # draw this bounding box
        image = draw_bounding_box(image, image_width, image_height, width, height, top, left, colors[i], i)
        i += 1
        if i > 2:
            break
    # write the image to a file
    cv2.imwrite('face_bounding_boxes.jpg', image)
    os.system('open -a Preview face_bounding_boxes.jpg')


# draw bounding boxe around one face
def draw_bounding_box(cv_img, cv_img_width, cv_img_height, width, height, top, left, color, i):
    # calculate bounding box coordinates top-left - x,y, bottom-right - x,y
    width_pixels = int(width * cv_img_width)
    height_pixels = int(height * cv_img_height)
    left_pixel = int(left * cv_img_width)
    top_pixel = int(top * cv_img_height)
    cv2.rectangle(cv_img,(left_pixel, top_pixel),(left_pixel+width_pixels, top_pixel+height_pixels),(color[1],color[2],color[3]),2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(cv_img, str(i + 1), (left_pixel + 5, top_pixel + height_pixels + 25), font, 0.8, (color[1],color[2],color[3]), 2)
    return cv_img


## START MAIN

# if no arguments take a photo
# if one argument open the image file and decode it
# if more than on argument exit gracefully and print usage guidance
if len(argv) == 1:
    encoded_image = take_photo(save=True)
elif len(argv) == 2:
    print ("opening image in file: ", argv[1])
    encoded_image=read_image(argv[1])
else:
    print ("Use with no arguments to take a photo with the camera, or one argument to use a saved image")
    exit(-1)

translate = 'ru'
labels=reko_detect_labels(encoded_image)
humans, labels_response_string = create_verbal_response_labels(labels)
print (bcolors.GREEN + labels_response_string + bcolors.ENDC)

with ignore_stderr():
    speak(labels_response_string)

if humans:
    print ("Detected Human: ", humans, "\n")
    reko_response = reko_detect_faces(encoded_image)
    faces_response_string = create_verbal_response_face(reko_response)
    save_image_with_bounding_boxes(encoded_image, reko_response)
    print (bcolors.GREEN + faces_response_string + bcolors.ENDC)
    sleep(1)
    with ignore_stderr():
        speak(faces_response_string)

    if translate:
        command = "aws translate translate-text --text '%s' --source-language-code en --target-language-code %s > tmp" % (faces_response_string, translate)
        translated = os.system(command)
        output = open('tmp', 'r')
        translation = json.load(output)
        print (bcolors.RED + '\n\n\nTranslated to %s' % translate)
        print (translation['TranslatedText'])
        speak (json.dumps(translation['TranslatedText'], ensure_ascii=False).encode('utf8'), "Lucia")
else:
    print ("No humans detected. Skipping facial recognition")
