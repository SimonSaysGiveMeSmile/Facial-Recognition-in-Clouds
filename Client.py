import cv2
import os
from socket import *
import pickle
import sys
from hashlib import sha256
import struct
from numpy import *
import base64

# Set up server address and port#

multicastGroup = ("235.1.1.1", 5000)

# Create a UDP socket

clientSocket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)

# set a timeout wait time for 1 second

clientSocket.settimeout(10)

# Set a ttl so that it can't leave the network/computer

ttl = struct.pack('b', 32)

clientSocket.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl)

requestNumber = 0


def takePicture(destination, nameID, requestNumber, portNumber):

    # increase the request number

    requestNumber += 1

    print("Press Space Bar to take picture")

    cam = cv2.VideoCapture(0)
   
    cv2.namedWindow('Picture')

    # while loop

    while True:

        # intializing the frame, ret

        ret, frame = cam.read()

        # the frame will show with the title of test

        cv2.imshow('Press Space Bar to take picture', frame)

        # if the spacebar key is been pressed screenshots will be taken

        if cv2.waitKey(1) == ord(' '):

            # saves the image as a png file

            encode_param=[int(cv2.IMWRITE_JPEG_QUALITY),90]

            result, imgencode = cv2.imencode('.jpg', frame, encode_param)

            data = array(imgencode)

            print('screenshot taken')

            cv2.destroyWindow('Press Space Bar to take picture')

            break

    # release the camera

    cam.release()

    # Send request to server

    pictureSocket = socket(AF_INET, SOCK_STREAM)

    print(destination)
    sock = pictureSocket.connect(("192.168.137.1", portNumber))

    print("a")

    # Timeout to give time for image transmition

    stringData = base64.b64encode(data)

    length = str(len(stringData))

    pictureSocket.sendall(length.encode('utf-8').ljust(64))

    pictureSocket.sendall(stringData)

    pictureSocket.close()

    try:

        lookingForMessage = True

        while lookingForMessage:

            # Obtain the return message

            response, server = clientSocket.recvfrom(2048)

            # convert the message to a useable format

            response = pickle.loads(response)

            # Check if it is for the most recent request

            print(type(response))

            if str(response[0]) == str(requestNumber):

                # get rid of the request number as it does not need to be printed

                response.pop(0)

                # Stop looking for correct message, stops while loop from going through another cycle

                lookingForMessage = False

                if str(response[0]) == "picture failed":

                    print("Face not detected, try again")

                    takePicture(response[-2], nameID, requestNumber, response[-1])

                else:

                    # Say what server provided the information

                    print("From Server: " + str(response[-1]))

    except:

        # notify there was a failure

        print(" Request time out\n")


def handleRequest(request, nameID, requestNumber):
    # increase the request number

    requestNumber += 1

    sendingMessage = [str(requestNumber), request, nameID]

    # Send request to server

    sent = clientSocket.sendto(pickle.dumps(sendingMessage), multicastGroup)

    try:

        lookingForMessage = True

        while lookingForMessage:

            # Obtain the return message

            returnMessage, server = clientSocket.recvfrom(2048)

            # convert the message to a useable format

            response = pickle.loads(returnMessage)

            # Check if it is for the most recent request

            if response[0] == str(requestNumber):

                # get rid of the request number as it does not need to be printed

                response.pop(0)

                # Stop looking for correct message, stops while loop from going through another cycle

                lookingForMessage = False

                if str(response[-3]) == "picture":

                    takePicture(response[-2], nameID, requestNumber, response[-1])

                else:

                    # Say what server said

                    print("From Server: " + str(response[-1]))

    except BaseException as e:

        # notify there was a failure

        print(" Request time out\n")

def FRC():

    while True:

        print(" ")

        print("This is app is not case sensitive")

        print(" ")

        # Printing instructions

        print("Please enter request below. Enter 'Help' to see a list of requests available")

        # Take their request

        request = str(input(": ")).lower()

        # Respond to request based on what was requested

        if request == "help":

            # Provide format instructions

            # print("For requests with multiple words please use a space between each word.")

            print(" ")

            # Provide a list of all possible requests

            print("'Register': Make a new authorized account")

            print("'Login': Attempt to gain access")

            print("'Quit'")

        elif request == "quit":

            break

        elif request == "register" or request == "login":

            nameID = sha256(str(input("Enter Username: ")).lower().encode('utf-8')).hexdigest()

            handleRequest(request, nameID, requestNumber)

        else:

            print("invalid request")

    # Close connection to server as requested

    clientSocket.close()

FRC()