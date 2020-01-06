import json
import boto3
import urllib
import logging
import io
import os
import base64
from PIL import Image, ImageDraw, ExifTags, ImageColor, ImageFont
from twython import Twython

kms = boto3.client('kms')
session = boto3.session.Session()

APP_KEY = kms.decrypt(CiphertextBlob=bytes(base64.b64decode(os.environ['EncryptedConsumerApiKey'])))['Plaintext']
APP_SECRET = kms.decrypt(CiphertextBlob=bytes(base64.b64decode(os.environ['EncryptedConsumerApiSecretKey'])))['Plaintext']
OAUTH_TOKEN = kms.decrypt(CiphertextBlob=bytes(base64.b64decode(os.environ['EncryptedConsumerOAUTHTOKEN'])))['Plaintext']
OAUTH_TOKEN_SECRET = kms.decrypt(CiphertextBlob=bytes(base64.b64decode(os.environ['EncryptedConsumerOAUTHSECRET'])))['Plaintext']

twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

model='arn:aws:rekognition:us-east-1:397652707012:project/Real_Humus/version/Real_Humus.2019-12-24T15.41.28/1577194888945'
min_confidence=60
region = 'us-east-1'

def lambda_handler(event, context):

    logger.info('Event Data: ' + json.dumps(event))

    file_object = event['Records'][0]['s3']['object']
    photo = file_object['key']
    bucket = event['Records'][0]['s3']['bucket']
    event_time = event['Records'][0]['eventTime']

    response = show_custom_labels(model, bucket['name'], photo, min_confidence)

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }

def decrypt(hash):
    return kms.decrypt(CiphertextBlob=b64decode(hash))['Plaintext']

def show_custom_labels(model,bucket,photo, min_confidence):

    client=boto3.client('rekognition', region_name=region)

    #Call DetectCustomLabels
    response = client.detect_custom_labels(Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
        MinConfidence=min_confidence,
        ProjectVersionArn=model)

    # Load image from S3 bucket
    s3_connection = boto3.client('s3')

    tags = s3_connection.get_object_tagging(
        Bucket=bucket,
        Key=photo
    )

    # Get a list of all tags
    tag_set = tags['TagSet']

    # Print out each tag
    for tag in tag_set:
        if tag['Key'] == 'twitter_id':
            twitter_id = tag['Value']
        if tag['Key'] == 'twitter_user':
            user_id = tag['Value']
        if tag['Key'] == 'additional_users':
            additional_users = tag['Value']

    if response:
        #s3_object = s3_connection.Object(bucket,photo)
        s3_response = s3_connection.get_object(
            Bucket=bucket,
            Key=photo
            )

        stream = io.BytesIO(s3_response['Body'].read())
        image=Image.open(stream)

        imgWidth, imgHeight = image.size
        draw = ImageDraw.Draw(image)


        # calculate and display bounding boxes for each detected custom label
        logger.info('Detected custom labels for ' + photo)
        text = ''

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

        customLabel = response['CustomLabels'][largest]
        logger.info('Label ' + str(customLabel['Name']))
        logger.info('Confidence ' + str(customLabel['Confidence']))

        if customLabel['Name'] == 'Humus' and 'Geometry' in customLabel:
            box = customLabel['Geometry']['BoundingBox']
            left = imgWidth * box['Left']
            top = imgHeight * box['Top']
            width = imgWidth * box['Width']
            height = imgHeight * box['Height']

            fnt = ImageFont.truetype('./Arial.ttf', 20)
            color = '#eb0924'

            if top>30:
                top_location = top-27
            else:
                top_location = top+10

            points = (
                (left,top),
                (left + width, top),
                (left + width, top + height),
                (left , top + height),
                (left, top))
            draw.line(points, fill=color, width=5)

            text = 'This is ' + customLabel['Name'] + ' - ' + str(round(customLabel['Confidence'], 2)) + '% Confidence'
            w, h = fnt.getsize(text)
            draw.rectangle((left,top_location, left+2 + w, top_location + h + 3), fill='white')
            draw.text((left+1,top_location), text, fill=color, font=fnt)
            logger.info(text)

        in_mem_file = io.BytesIO()
        image.save(in_mem_file, format=image.format)
        in_mem_file.seek(0)

        twitter_resp = twitter.upload_media(media=in_mem_file)
        if text:
            response = twitter.update_status(status=('@%s %sThis is what I see...\nFollow @HumusNotHumus') % (user_id, additional_users), media_ids=twitter_resp['media_id'], in_reply_to_status_id=twitter_id)
        else:
            response = twitter.update_status(status=('@%s %sSorry, no Humus here!\nFollow @HumusNotHumus') % (user_id, additional_users), media_ids=twitter_resp['media_id'], in_reply_to_status_id=twitter_id)

        logger.info(json.dumps(response))

        return {'message' : 'Found labels'}

    else:
        response = twitter.update_status(status=('@%s Sorry, no Humus here!\nFollow @HumusNotHumus') % (user_id), in_reply_to_status_id=twitter_id)

        logger.info(json.dumps(response))

        return {'message' : 'No labels'}
