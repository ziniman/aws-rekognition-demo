#!/usr/bin/python

import boto3
import os
import json
import argparse

class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

# command line arguments
parser = argparse.ArgumentParser(description='Match face from image file with Rekognition collection')
parser.add_argument('image', help='Souece image name')
parser.add_argument('collection', help='Collection name')
parser.add_argument('region', default='us-east-1', nargs='?', help='Comprehend region (default=us-east-1')
args = parser.parse_args()
print(args)

if __name__ == "__main__":

    bucket='bucket'
    collectionId=args.collection
    fileName=args.image
    threshold = 50
    maxFaces=1

    client=boto3.client('rekognition')
    os.system('open -a Preview %s' % fileName)

    imageSource=open(fileName,'rb')

    response=client.search_faces_by_image(CollectionId=collectionId,
                                Image={'Bytes': imageSource.read()},
                                FaceMatchThreshold=threshold,
                                MaxFaces=maxFaces)

    print json.dumps(response, sort_keys=True, indent=4)

    faceMatches=response['FaceMatches']
    if not faceMatches:
        print bcolors.RED + 'No Match!'
    else:
        print ('Matching faces')
        for match in faceMatches:
                print (bcolors.BLUE + 'FaceId: ' + match['Face']['FaceId'])
                print (bcolors.BLUE + 'FaceTag: ' + bcolors.GREEN + match['Face']['ExternalImageId'].upper())
                print (bcolors.BLUE + 'Similarity: ' + bcolors.GREEN + "{:.2f}".format(match['Similarity']) + "%")
