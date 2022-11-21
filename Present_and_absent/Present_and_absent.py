import os
import re
import time
import cv2
import face_recognition
import numpy as np
import requests
from datetime import datetime
from cvzone.HandTrackingModule import HandDetector
from collections import OrderedDict

# cvzone version 1.4.1 or earlier
# mediapipe version 0.8.7.3 or earlier

PATH = 'faces'
FIRST_SENDING_TIME = -1
DETECTOR = HandDetector(detectionCon=0.8)

images = []
class_names = []
class_names_copy = []
recognized_names = []
sended_names_counter = []
times_list = []
fingers_id = [4, 8, 12, 16, 20]
images_list = os.listdir(PATH)

# Loading bot and Telegram channel data from a file:

BOT_AND_CHAT_DATA = open('bot_and_chat_data.txt', 'r')
BOT_TOKEN = BOT_AND_CHAT_DATA.readline().strip()
CHAT_ID = BOT_AND_CHAT_DATA.readline().strip()
BOT_AND_CHAT_DATA.close()

# Clearing a text file before starting work:

open('day_list_of_students.txt', 'w', encoding="utf-8").close()

# Dictionary for correct transliteration of names into another language:

def transliterate(name):
    dictionary = {
        'Andrej': 'Andrej',
        'Oleh': 'Oleh',
        'Nastya':'Anastázia'
    }
    for key in dictionary:
        name = name.replace(key, dictionary[key])
    return name

# Convert photos to grayscale and then digitally encode faces:

def find_encodings(images: list) -> list:
    encoded_images = []
    for IMG in images:
        IMG = cv2.cvtColor(IMG, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(IMG)[0]
        encoded_images.append(encode)
    return encoded_images

# Saving the names of persons and the time they were added to a special EXCEL file:

def mark_attendance(name):
    with open("NameList.csv", "r+") as f:
        data_list = f.readlines()
        name_list = []
        for line in data_list:
            entry = line.split(',')
            name_list.append(entry[0])
        if name not in name_list:
            now = datetime.now()
            dtString = now.strftime("%H:%M:%S")
            f.writelines(f'\n{name}, {dtString}')

# Implementation of the function of sending a message through a bot in Telegram:

def telegrambot_sendmsg(BOT_TOKEN, CHAT_ID, message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&parse_mode=Markdown&text={message}'
    try:
        response = requests.get(url)
        return response.json()
    except ConnectionError:
        return 0

# Function to replace the word "departed" with an empty character:

def replace_it(word):
    word = word.replace('departed', '')
    return word

# Function to remove copies from the list:

def delete_copies(enrty_list):
    list_copy = list(OrderedDict.fromkeys(enrty_list))
    return list_copy

# Function that allows the user to set the start time for sending the list of absentees:

def time_input():
    first_sending_time = 0
    string_first_time = input(
        "Enter when you want to send the list for the first time (for example: 00:19, 01:19 8:00): ")
    if string_first_time.find(":") > -1 and len(string_first_time) == 5:
        try:
            if int(string_first_time[0:2]) > -1 and int(string_first_time[0:2]) < 25 and int(
                    string_first_time[3:6]) > -1 and int(string_first_time[3:6]) < 61:

                if int(time.strftime("%H")) * 60 + int(time.strftime("%M")) <= int(
                    string_first_time[0:2]) * 60 + int(string_first_time[3:6]):
                    
                    first_sending_time = int(string_first_time[0:2]) * 60 + int(string_first_time[3:6])
                else:
                    first_sending_time = time_input()
            else:
                first_sending_time = time_input()
        except ValueError:
            first_sending_time = time_input()
    else:
        first_sending_time = time_input()

    return first_sending_time

# A function that allows the user to set the intervals at which absentee lists will be sent:

def finally_number_input(message_to_user, condition):
    number = 0
    set_number = input(message_to_user)
    try:
        set_number = int(set_number)
        if set_number > condition:
            number = set_number
        else:
            number = finally_number_input(message_to_user, condition)
    except ValueError:
        number = finally_number_input(message_to_user, condition)
    return number

def interval_input(n, first_time):
    intervals_list = []
    intervals_list.append(first_time)

    choose_interval_command = input("Do the subjects in your school/university have different lengths? [y,n] ")

    if choose_interval_command == "n":
        set_one_interval = input(
            "Please write the length (in minutes) of one subject at your school/university? (ex.: 110, 80, 60, 45): ")
        try:
            for i in range (n):
                intervals_list.append(int(set_one_interval))
        except ValueError:
            intervals_list.clear()
            intervals_list = interval_input(n, first_time)

    elif choose_interval_command == "y":
        try:
            for i in range (n):
                set_multi_interval = int(input(f"Please enter the length of the {i+1} subject (in minutes): "))
                intervals_list.append(set_multi_interval)
        except ValueError:
            intervals_list.clear()
            intervals_list = interval_input(n, first_time)
    else:
        intervals_list.clear()
        intervals_list = interval_input(n, first_time)

    return intervals_list

def writing_in_file(which_time, is_null_on_first_place, BOT_TOKEN, CHAT_ID):
    write_string = "By " + str(int(which_time / 60)) + ":"
    if is_null_on_first_place:
        write_string += "0"
    else:
        pass
    write_string += str(which_time % 60) + " haven't arrived:"
    write_string += '\n'

    return write_string

def form_message_to_bot(file, result, writing_in_file_result, BOT_TOKEN, CHAT_ID):
    recognized_list_to_bot = writing_in_file_result
    recognized = []
    for i in range(len(result)):
        if result[i] != "teacher" and re.sub(r'[^\w\s]+|[\d]+', r'', result[i]).strip() != "departed":
            recognized.append(transliterate(str(result[i])))
    recognized.sort()
    for j in range(len(recognized)):
        recognized_list_to_bot += str(j + 1) + ") " + recognized[j] + "\n"
    response = telegrambot_sendmsg(BOT_TOKEN, CHAT_ID, recognized_list_to_bot)

    file.write(recognized_list_to_bot)
    file.write('\n\n')

def time_comparing(NowTime, TN_index, class_names,
                   recognized_names, sended_names_counter, BOT_TOKEN,
                   CHAT_ID, file, times_list):
    if NowTime == times_list[TN_index] and sended_names_counter[TN_index] == 0:
        result = list(set(recognized_names) ^ set(class_names))
        writing_in_file_result = ""
        if times_list[TN_index] % 60 >= 10:
            writing_in_file_result = writing_in_file(times_list[TN_index],
                                                     False, BOT_TOKEN, CHAT_ID)
        else:
            writing_in_file_result = writing_in_file(times_list[TN_index],
                                                     True, BOT_TOKEN, CHAT_ID)

        form_message_to_bot(file, result, writing_in_file_result, BOT_TOKEN, CHAT_ID)
        sended_names_counter[TN_index] += 1
    else:
        pass

def times_list_generation(n):

    first_time = time_input()

    times_generated_list = []
    times_generated_list = interval_input(n, first_time)

    if n > 1:
        for i in range (2, n + 1):
            times_generated_list[i] += finally_number_input(
                f"Write the length of the break between the {i - 1} and {i} lesson (in minutes): ", -1)

        for i in range (1, n + 1):
            times_generated_list[i] += times_generated_list[i - 1]

    return times_generated_list, len(times_generated_list)

# Face recognition in photos, convert them to digital format and create a list of names:

for cls in images_list:
    current_image = cv2.imread(f'{PATH}/{cls}')
    images.append(current_image)
    if re.sub(r'[^\w\s]+|[\d]+', r'', os.path.splitext(cls)[0]).strip() != "teacher":
        class_names.append(os.path.splitext(cls)[0])
    else:
        class_names.append("teacher")

encodeListKnown = find_encodings(images)
print("Decoding completed")

lessons_number = finally_number_input("Enter the number of lessons today: ", 0)
times_list, nt_counter_length = times_list_generation(lessons_number)

for i in range (nt_counter_length):
    sended_names_counter.append(0)

# Camera connection:

cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Saving finger images in a separate list:

folder_path = "FingerImages"
images_list = os.listdir(folder_path)
overlayList = []

for image_path in images_list:
    image = cv2.imread(f'{folder_path}/{image_path}')
    overlayList.append(image)

class_names_copy = class_names.copy()

while True:

    # Processing hand images
    #  and positioning text on the camera window:

    total_fingers = 0
    success, IMG = cap.read()
    IMG = DETECTOR.findHands(IMG)
    positions_list, _ = DETECTOR.findPosition(IMG, draw=False)
    cv2.putText(IMG, "PLEASE LOOK AT THE CAMERA FOR 2 SECONDS", (25, 25),
                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 255), 2)
    cv2.putText(IMG, "MAKE AS NEUTRAL A FACE AS POSSIBLE", (25, 50),
                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 255), 2)
    imgS = cv2.resize(IMG, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    if len(positions_list) != 0:
        fingers = []

        # Thumb:

        if positions_list[fingers_id[0]][0] > positions_list[fingers_id[0] - 1][0]:
            fingers.append(1)
        else:
            fingers.append(0)
        # 4 Fingers:

        for id in range(1, 5):
            if positions_list[fingers_id[id]][1] < positions_list[fingers_id[id] - 2][1]:
                fingers.append(1)
            else:
                fingers.append(0)

        # Counting the number of fingers:

        totalFingers = fingers.count(1)
        total_fingers = int(totalFingers)

        # Placement of the number of fingers on the camera's screen:

        h, w, c = overlayList[totalFingers - 1].shape
        IMG[0:h, 1040:w + 1040] = overlayList[totalFingers - 1] 
        # FOR NORMAL WORK SHOW YOUR RIGHT HAND WITH THE PALM TO THE CAMERA AND THE LEFT - VICE VERSA
        cv2.putText(IMG, str(totalFingers), (1190, 100), cv2.FONT_HERSHEY_PLAIN,
                    5, (255, 0, 0), 3)

    # Face detection on the current frame:

    faces_current_frame = face_recognition.face_locations(imgS)
    encode_current_frame = face_recognition.face_encodings(imgS, faces_current_frame)

    # Comparing face points with a list of faces,
    # finding the face ID and identifying a person by ID:

    for encodeFace, faceLoc in zip(encode_current_frame, faces_current_frame):
        matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
        matchIndex = np.argmin(faceDis)
        if matches[matchIndex]:
            name = class_names[matchIndex]
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

            # Highlighting a recognized face with a green
            # rectangle with the person's name

            cv2.rectangle(IMG, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(IMG, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
            counter = 0

            # Replacing a person's name with the standard name
            # of an absent student if they show 3 fingers and a face:

            for i in range(len(recognized_names)):
                if recognized_names[i] == name and total_fingers == 3:
                    for j in range(len(class_names)):
                        if (class_names[j] == name):
                            class_names[j] = "departed" + str(j)
                elif (re.sub(r'[^\w\s]+|[\d]+', r'', name).strip() == "departed" and total_fingers == 4):
                    class_names[int(replace_it(name))] = class_names_copy[int(replace_it(name))]
                elif recognized_names[i] == name and total_fingers != 3:
                    counter += 1
                elif name == "" and total_fingers == 3:
                    counter += 1
                else:
                    counter = 0

            # Displaying a person's name on the screen according to the list:

            if counter < 1:
                if re.sub(r'[^\w\s]+|[\d]+', r'', name).strip() != "departed" and name != "teacher":
                    recognized_names.append(name)
                    cv2.putText(IMG, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    mark_attendance(name)
                    recognized_names = delete_copies(recognized_names)
            else:
                cv2.putText(IMG, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

    # Determining the current time:

    NowTime = int(time.strftime("%H")) * 60 + int(time.strftime("%M"))

    # The output of the program will also be copied to this file:

    F0 = open('day_list_of_students.txt', 'a', encoding="utf-8")

    # Saving the list of absentees in the morning in a text file,
    # as well as sending this list through the
    # chat bot to the Telegram channel:

    for i in range(nt_counter_length):
        time_comparing (NowTime, i, class_names, recognized_names, sended_names_counter,
                       BOT_TOKEN, CHAT_ID, F0, times_list)

    F0.close()

    cv2.imshow("YOU", IMG)
    cv2.waitKey(1)