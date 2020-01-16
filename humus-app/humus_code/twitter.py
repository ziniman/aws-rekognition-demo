import json
import boto3
import urllib
import logging
import io
import requests
from PIL import Image, ImageDraw, ExifTags, ImageColor, ImageFont

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region = 'us-east-1'

banned_account=['OrganicGrowMID']

def lambda_handler(event, context):

    logger.info('Event Data: ' + json.dumps(event))

    for item in event:
        retweet_id = ''
        media = ''
        additional_users = ''

        try:
            retweet_id = item["retweeted_status"]["id_str"]
            logger.info("Retweet - Moving to next")
            continue
        except KeyError:
            logger.info("Not a retweet")

        try:
            media = item["extended_entities"]["media"]
            logger.info("Found Media")
        except KeyError:
            logger.info("No Media - Moving to next")
            continue

        image_url = (item["entities"]["media"][0]["media_url"])
        item_id = (item["id_str"])
        user_id = (item["user"]["screen_name"])

        if user_id in banned_account:
            continue

        try:
            for user in item["entities"]["user_mentions"]:
                additional_users = additional_users + '@' + user["screen_name"] + ' '
        except KeyError:
            logger.info("No Additional Users")

        response = requests.get(image_url)
        image = Image.open(io.BytesIO(response.content))

        in_mem_file = io.BytesIO()
        image.save(in_mem_file, format=image.format)
        in_mem_file.seek(0)

        # Upload image to s3
        s3_connection = boto3.client('s3')

        upload_key = 'uploads/' + item_id + '.jpg'

        s3_connection.upload_fileobj(
            in_mem_file,
            'twitter-income-humus',
            upload_key
        )

        response = s3_connection.put_object_tagging(
            Bucket='twitter-income-humus',
            Key=upload_key,
            Tagging={
                'TagSet': [
                    {
                        'Key': 'twitter_id',
                        'Value': item_id
                    },
                    {
                        'Key': 'twitter_user',
                        'Value': user_id
                    },
                    {
                        'Key': 'additional_users',
                        'Value': additional_users
                    },
                ]
            }
        )
        logger.info('Wrote file and tags to S3 - ' + upload_key)

    response = "{'Wrote file(s) and tags to S3'}"

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }
