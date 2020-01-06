#!/usr/bin/python

#Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#PDX-License-Identifier: MIT-0 (For details, see https://github.com/awsdocs/amazon-rekognition-developer-guide/blob/master/LICENSE-SAMPLECODE.)

import boto3
import io
from PIL import Image, ImageDraw, ExifTags, ImageColor, ImageFont

region = 'us-east-1'

def show_custom_labels(model,bucket,photo, min_confidence):


    client=boto3.client('rekognition', region_name=region)

    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')

    s3_object = s3_connection.Object(bucket,photo)
    s3_response = s3_object.get()

    stream = io.BytesIO(s3_response['Body'].read())
    image=Image.open(stream)

    #Call DetectCustomLabels
    response = client.detect_custom_labels(Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
        MinConfidence=min_confidence,
        ProjectVersionArn=model)


    imgWidth, imgHeight = image.size
    draw = ImageDraw.Draw(image)


    # calculate and display bounding boxes for each detected custom label
    print('Detected custom labels for ' + photo)

    max_w = 0
    c = 0
    largest = 0

    for customLabel in response['CustomLabels']:
        print('Label ' + str(customLabel['Name']))
        print('Confidence ' + str(customLabel['Confidence']))
        if customLabel['Name'] == 'Humus' and 'Geometry' in customLabel:
            box = customLabel['Geometry']['BoundingBox']
            width = imgWidth * box['Width']

            if width>max_w:
                largest = c
                max_w = width
        c += 1

    print(largest)
    customLabel = response['CustomLabels'][largest]
    print('Label ' + str(customLabel['Name']))
    print('Confidence ' + str(customLabel['Confidence']))
    if customLabel['Name'] == 'Humus' and 'Geometry' in customLabel:
        box = customLabel['Geometry']['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']

        if width>max_w:
            largest = c
            max_w = width

        fnt = ImageFont.truetype('/Library/Fonts/Arial.ttf', 30)
        if customLabel['Name'] == 'Humus':
            color = '#00cc00'
        else:
            color = '#d40000'

        draw.text((left+10,top+10), customLabel['Name'] + ' - ' + str(customLabel['Confidence']) + '%', fill=color, font=fnt)

        print('Left: ' + '{0:.0f}'.format(left))
        print('Top: ' + '{0:.0f}'.format(top))
        print('Face Width: ' + "{0:.0f}".format(width))
        print('Face Height: ' + "{0:.0f}".format(height))

        points = (
            (left,top),
            (left + width, top),
            (left + width, top + height),
            (left , top + height),
            (left, top))
        draw.line(points, fill=color, width=3)


    image.show()

    return len(response['CustomLabels'])

def main():

    bucket="sagemaker-humus"
    photo="Humus/libat.jpg"
    model='arn:aws:rekognition:us-east-1:397652707012:project/Real_Humus/version/Real_Humus.2019-12-24T15.41.28/1577194888945'
    min_confidence=50

    label_count=show_custom_labels(model,bucket,photo, min_confidence)
    print("Custom labels detected: " + str(label_count))


if __name__ == "__main__":
    main()
