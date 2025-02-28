from socket import *
import pickle
import os, sys
import struct
from array import *
import random
import threading
from time import *
import face_recognition
import cv2
from numpy import *
import math
import base64

ID = os.getpid()

print("Server " + str(ID) + " created")

multicastGroup = "235.1.1.1"

serverPort = 55555

Leader = False

LeaderAlive = False

# Create a UDP socket

serverSocket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)

# allow multiple sockets to use the same PORT number

serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

# Assign IP address and port number to socket

serverSocket.bind(("", serverPort))

# connect to multicast group

group = inet_aton(multicastGroup)

mreq = struct.pack('4sL', group, INADDR_ANY)

serverSocket.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)

serverSocket.settimeout(1)

# Fix working directory for file calls

os.chdir(os.path.dirname(os.path.realpath(__file__)))

os.chdir(os.path.join(os.getcwd(), "images"))

accountsRegistered = {}

for file in os.listdir(os.getcwd()):
    accountsRegistered[os.path.splitext(file)[0]] = load(file)
    #print(accountsRegistered[os.path.splitext(file)[0]])

print("Server is Ready")


def face_confidence(face_distance, face_match_threshold=0.6):
    range = (1.0 - face_match_threshold)

    linear_val = (1.0 - face_distance) / (range * 2.0)

    if face_distance > face_match_threshold:

        return round(linear_val * 100, 2)

    else:

        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100

        return round(value, 2)


def claimLeadership():
    global Leader

    global LeaderAlive

    serverSocket.sendto(pickle.dumps([0, "Leader " + str(ID)]), (multicastGroup, serverPort))

    Leader = True

    LeaderAlive = True

    # print("This Server is now the Leader")


def requestLeadership():
    WaitingForResponse = True

    # print("This Server is Requesting to be Leader in Election")

    serverSocket.sendto(pickle.dumps([0, "Request " + str(ID)]), (multicastGroup, serverPort))

    try:

        while WaitingForResponse:

            # Obtain the return message

            Message, address = serverSocket.recvfrom(2048)

            # convert the message to a useable format

            response = pickle.loads(Message)

            # Check if it is for the most recent request

            if str(response[0]) == "0" and str(response[1]) == "Denied" and str(response[2]) == str(ID):
                # Stop looking for correct message, stops while loop from going through another cycle

                WaitingForResponse = False

                # print("This Server will not be Leader")

    # point in which we assume no one is contesting leader request

    except timeout:

        claimLeadership()


def handleElection(request, address):
    global Leader

    global LeaderAlive

    # print(request)

    if str(request) == "ping" and Leader == True:

        serverSocket.sendto(pickle.dumps([0, "pong"]), address)

    elif str(request) != "ping" and str(request) != "pong":

        requestList = request.split()

        # A server is requesting to be leader

        if str(requestList[0]) == "Request" and (int(requestList[1]) < int(ID)):

            serverSocket.sendto(pickle.dumps([0, "Denied", str(requestList[1])]), address)

            # print("Sending Denial of leadership to " + str(requestList[1]))

        # Server claimed leadership when they were not supposed to, probably from a delayed response

        elif str(requestList[0]) == "Leader" and int(requestList[1]) < int(ID):

            requestLeadership()

        elif str(requestList[0]) == "Leader" and int(requestList[1]) > int(ID):

            Leader = False

            LeaderAlive = True

            # print("Leader is now Server " + requestList[1])


def pingLeader():
    global LeaderAlive

    serverSocket.sendto(pickle.dumps([0, "ping"]), (multicastGroup, serverPort))

    WaitingForLeadersResponse = True

    try:

        while WaitingForLeadersResponse:

            # Obtain the return message

            Message, address = serverSocket.recvfrom(2048)

            # convert the message to a useable format

            response = pickle.loads(Message)

            # Check if it is the desired response

            if str(response[0]) == "0" and str(response[1]) == "pong":
                # Stop looking for correct message, stops while loop from going through another cycle

                WaitingForLeadersResponse = False

                LeaderAlive = True

    # point in which we assume leader is no longer functioning

    except timeout:

        if not Leader:
            LeaderAlive = False

            # print("No Leader Detected")

            requestLeadership()


def recvall(socket, count):
    buf = b''

    while count:

        newbuf = socket.recv(count)

        if not newbuf: return None

        buf += newbuf

        count -= len(newbuf)

    return buf


def FaceCompare(known_encoding, face_encoding):

    match = face_recognition.compare_faces(known_encoding, face_encoding)

    confidence = 0

    # Calculate the shortest distance to face

    face_distances = face_recognition.face_distance(known_encoding, face_encoding)

    best_match_index = argmin(face_distances)

    if match[best_match_index]:

        confidence = face_confidence(face_distances[best_match_index])

    return confidence

def requestPicture(requestNumber, request, nameID, message, address):  # recursive function

    global accountsRegistered

    pictureSocket = socket(AF_INET, SOCK_STREAM)

    pictureSocket.bind(('localhost', 55557))

    serverSocket.sendto(pickle.dumps([requestNumber, message]), address)

    print("Picture request sent")

    pictureSocket.listen(1)

    conn, addr = pictureSocket.accept()

    len = recvall(conn, 64)

    length1 = len.decode('utf-8')

    stringData = recvall(conn, int(length1))

    data = frombuffer(base64.b64decode(stringData), uint8)

    img = cv2.imdecode(data, 1)

    pictureSocket.close()

    try:

        # Resize img to 1/4 size for faster face recognition processing

        small_frame = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)

        rgb_small_frame = small_frame[:, :, ::-1]

        # Find all the faces and face encodings in the current frame of video

        face_locations = face_recognition.face_locations(rgb_small_frame)

        face_encoding = face_recognition.face_encodings(rgb_small_frame, face_locations)

        if request == "register":

            accountsRegistered[nameID] = face_encoding

            # Save encoding in data base

            save(nameID + '.npy', face_encoding)

            return ([str(int(requestNumber) + 1), "Registered Successful"])

        else:  # (must be login request)

            confidence = FaceCompare(array(accountsRegistered[nameID]), face_encoding)

            if confidence >= 95:

                #Updated saved image ith more recent image
                accountsRegistered[nameID] = face_encoding
                save(nameID + '.npy', face_encoding)

                return ([str(int(requestNumber) + 1), "Login Successful: Access Granted"])

            else:
                return ([str(int(requestNumber) + 1), "Login Failed: Face does not match username"])

    except:

        return requestPicture(str(int(requestNumber) + 1), request, nameID, "picture failed", address)


def handleRequest(requestNumber, request, nameID, address):
    response = [requestNumber]

    # If a picture is required, send to next function

    if (request == "login" and nameID in accountsRegistered) or (

            request == "register" and nameID not in accountsRegistered):

        response = requestPicture(requestNumber, request, nameID, "picture", address)

    elif request == "login" and nameID not in accountsRegistered:

        response.append("No account exists with that username")

    elif request == "register" and nameID in accountsRegistered:

        response.append("Username already Taken")

    else:  # Client should make this never possible but just incase

        response.append("Invalid Request")

    # Send the response to the client

    print(type(response))

    serverSocket.sendto(pickle.dumps(response), address)


# Override the thread constructor and run() to fit the needs of this server


class myThread(threading.Thread):

    def __init__(self, number, request, nameID, address):
        threading.Thread.__init__(self)

        self.threadID = str(nameID)

        self.number = number

        self.request = request

        self.nameID = nameID

        self.address = address

    def run(self):
        # Show that the thread was created

        # print ("Starting Thread" + self.threadID + " at " + str(ctime(time()))) #optional

        # Call a function to process the request and respond

        handleRequest(self.number, self.request, self.nameID, self.address)

        # Show that the Thread has finished it's job

        # print ("Exiting Thread" + self.threadID + " at " + str(ctime(time()))) #optional


class PingingThread(threading.Thread):

    def __init__(self, interval):

        threading.Thread.__init__(self)

        self.interval = interval

    def run(self):

        global Leader

        global LeaderAlive

        while True:

            if LeaderAlive and not Leader:
                pingLeader()

            sleep(self.interval)


# Start thread responsible for pinging Leader to monitor its existance


thread = PingingThread(1)

thread.start()

# Call election to see if this server should be the Leader

requestLeadership()

while True:

    try:

        # Receive the client packet along with the address it is coming from

        receivedMessage, address = serverSocket.recvfrom(2048)

        receivedMessage = pickle.loads(receivedMessage)

        # If it is associated with election

        if receivedMessage[0] == 0:

            handleElection(receivedMessage[1], (multicastGroup, serverPort))

        elif Leader:

            print("Message arrived")

            # Make new thread with all information needed to handle the request

            thread = myThread(receivedMessage[0], receivedMessage[1], receivedMessage[2], address)

            # Tell the thread to run/start

            thread.start()

    except:

        continue