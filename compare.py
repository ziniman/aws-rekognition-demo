#!/usr/local/bin/python3

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
parser = argparse.ArgumentParser(description='Compare faces in 2 image file with Rekognition')
parser.add_argument('source', help='Souece image name')
parser.add_argument('target', help='Target image name')
parser.add_argument('region', default='us-east-1', nargs='?', help='Comprehend region (default=us-east-1')
args = parser.parse_args()
print(args)

if __name__ == "__main__":

    sourceFile=args.source
    targetFile=args.target

    os.system('open -a Preview %s' % sourceFile)
    os.system('open -a Preview %s' % targetFile)
    client=boto3.client('rekognition')

    imageSource=open(sourceFile,'rb')
    imageTarget=open(targetFile,'rb')

    response=client.compare_faces(SimilarityThreshold=80,
                                  SourceImage={'Bytes': imageSource.read()},
                                  TargetImage={'Bytes': imageTarget.read()})

    #print json.dumps(response, sort_keys=True, indent=4)
    os.system('echo "%s">%s' % (json.dumps(response, sort_keys=True, indent=4), 'last_compare.log'))

    if not response['FaceMatches']:
        print (bcolors.RED + 'No Match')
    else:
        for faceMatch in response['FaceMatches']:
            position = faceMatch['Face']['BoundingBox']
            confidence = str(faceMatch['Similarity'])
            if faceMatch['Similarity'] >= 85:
               print(bcolors.GREEN + 'The faces match with ' + confidence + '% confidence')
            else:
               print(bcolors.YELLOW + 'The faces match with ' + confidence + '% confidence')

    imageSource.close()
    imageTarget.close()
