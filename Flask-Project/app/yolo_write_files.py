#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import sys

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
import cv2
import numpy as np
import time
import pymysql
import mysql.connector
import pandas as pd

pymysql.install_as_MySQLdb()


# con = pymysql.connect('localhost', 'testuser', 'test623', 'testdb')


def start_detection(file_list, dbname, label='person'):
    config = {
        'user': 'root',
        'password': 'root',
        'host': 'db',
        'port': '3306',
        'database': 'yolo_frames'
    }
    con = mysql.connector.connect(**config)
    first_start_time = time.time()

    # Load yolo
    net = cv2.dnn.readNet("project_files/yolov3.weights.1",
                          "project_files/darknet/cfg/yolov3.cfg")
    classes = []
    with open("project_files/coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]

    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    colors = np.random.uniform(0, 255, size=(len(classes), 3))

    # Start detecting
    # open connection to mysql
    # with con:
    cur = con.cursor()
    drop_table_query = "DROP TABLE IF EXISTS {}".format(dbname)
    cur.execute(drop_table_query)
    create_table_query = "CREATE TABLE {}(Id INT PRIMARY KEY AUTO_INCREMENT, FrameNum INT, x INT, y INT, w INT, " \
                         "h INT, t TIMESTAMP, hr INT, min INT, sec INT)".format(dbname)
    cur.execute(create_table_query)
    for file_name in file_list:
        cap = cv2.VideoCapture(file_name)
        frame_count = 0
        img_array = []
        metadata_file = file_name.split('.')[0] + '.txt'
        video_output = file_name.split('.')[0] + '_yolo.avi'
        label_index = classes.index(label)
        outF = open(metadata_file, "w")
        # outF.write("FrameNum, x, y, w, h, t, hr, min, sec\n")
        while True:
            _, frame = cap.read()
            frame_count += 1
            if not _:
                break

            height, width, channels = frame.shape
            blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            net.setInput(blob)
            outs = net.forward(output_layers)

            class_ids = []
            confidences = []
            boxes = []

            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.5 and class_id == label_index:
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)

                        # draw circle
                        cv2.circle(frame, (center_x, center_y), radius=5, color=(0, 255, 0), thickness=1)
                        w = int(detection[2] * width)
                        h = int(detection[3] * width)

                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.4, 0.6)
            font = cv2.FONT_HERSHEY_PLAIN

            for i in range(len(boxes)):
                if i in indexes:
                    x, y, w, h = boxes[i]
                    label = str(classes[class_ids[i]])
                    color = colors[i]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(frame, label, (x, y + 30), font, 1, color, 2)

                    # create a text file to output bounding boxes
                    # write frame number and coordinates
                    t = time.localtime()
                    hour = t.tm_hour
                    minute = t.tm_min
                    seconds = t.tm_sec
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', t)
                    outF.write("FrameNum=%s, x=%f, y=%f, w=%f, h=%f, t=%s, hr=%f, min=%f, sec=%f\n" % (
                        frame_count, x, y, w, h, timestamp, hour, minute, seconds))
                    # outF.write("%s, %f, %f, %f, %f, %s, %f, %f, %f\n" % (
                    #     frame_count, x, y, w, h, timestamp, hour, minute, seconds))
                    insert_row_query = "INSERT INTO {}(FrameNum,x,y,w,h,t,hr,min,sec) VALUES({},{},{},{},{},{},{},{},{}) ".format(
                        dbname, frame_count, x, y, w, h, 'CURRENT_TIMESTAMP', hour, minute, seconds)
                    cur.execute(insert_row_query)
                    # outF.write("FrameNum=%s, x=%f, y=%f, w=%f, h=%f\n" % (frame_count, x, y, w, h))

            img_array.append(frame)
        key = cv2.waitKey(1)
        if key == 27:
            break
        cap.release()
        cv2.destroyAllWindows()
        outF.close()

        # Create the output video file
        size = (width, height)
        out = cv2.VideoWriter(video_output, cv2.VideoWriter_fourcc(*'DIVX'), 15, size)

        for i in range(len(img_array) - 1):
            out.write(img_array[i])
        out.release()

    # df = ttp.convert()

    cur.execute('SELECT * from {}'.format(dbname))
    df = pd.DataFrame(cur.fetchall())
    cur.close()
    con.close()
    # return "--- %s seconds ---" % (time.time() - first_start_time)
    # return str(df.shape[0])
    # return str(type(df))
    # return row
    return
