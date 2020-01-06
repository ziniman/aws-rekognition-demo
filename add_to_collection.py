#!/usr/bin/python

import boto3
import argparse
import os

parser = argparse.ArgumentParser(description='Add face from image file/folder to Rekognition collection')
parser.add_argument('image', help='Souece image/folder name')
parser.add_argument('collection', help='Collection name')
parser.add_argument('create_collection', default=0, nargs='?', help='Create New Collection (0/1)')
parser.add_argument('region', default='eu-west-1', nargs='?', help='Rekognition region (default=eu-west-1')
args = parser.parse_args()
print(args)

def add_faces_to_collection(photo, photo_id, collection_id):

    client=boto3.client('rekognition')

    response=client.index_faces(CollectionId=collection_id,
                                Image={'Bytes': photo},
                                ExternalImageId=photo_id,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])

    print ('Results for ' + photo_id)
    print('Faces indexed:')
    for faceRecord in response['FaceRecords']:
         print('  Face ID: ' + faceRecord['Face']['FaceId'])
         print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)
    return len(response['FaceRecords'])

def add_file(file):
    collection_id=args.collection

    filename, file_extension = os.path.splitext(os.path.basename(file))
    imageSource=open(file,'r')

    print ("%s - %s - %s") % (file, filename, collection_id)

    indexed_faces_count=add_faces_to_collection(imageSource.read(), filename.replace(" ", "_"), collection_id)
    print("Faces indexed count: " + str(indexed_faces_count))

def main():

    image = args.image

    if os.path.isdir(image):
        print "is dir"
        files = os.listdir(image)
        for f in files:
            add_file(image + '/' + f)
    else:
            add_file(image)

if __name__ == "__main__":
    main()
