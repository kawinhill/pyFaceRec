import time
from line_notification import LineNotify, TokenErrorException
from tkinter import messagebox
import cv2
import face_recognition
from datetime import datetime
import io
from multiprocessor import next_id, prev_id
from UltraDict import UltraDict
from PIL import Image
from shared_lock import SHARED_LOCK
from database import Database

config_dict = UltraDict(name="config",shared_lock=SHARED_LOCK,recurse=True)

# Use cnn if you have CUDA
#MODEL="hog"
MODEL="cnn"
# TOLERANCE = 0.5
# DELAY_BEFORE_ADD_NEW_LOGS = 5


def process(capture_id, worker_id, worker_num):

    Global = UltraDict(name='global', shared_lock=SHARED_LOCK)
    found_cam = UltraDict(name='found_cam', shared_lock=SHARED_LOCK)
    found_face_data = UltraDict(name='found_face_data', shared_lock=SHARED_LOCK)
    db = Database()

    frames_since_last_process = 0
    face_locations = []
    face_encodings = []

    read_frame_list = UltraDict(name='read_frame_list')
    write_frame_list = UltraDict(name='write_frame_list')
    active_cam = UltraDict(name='active_cam', shared_lock=SHARED_LOCK)
    buff_num = UltraDict(name='buff_num', shared_lock=SHARED_LOCK)
    read_num = UltraDict(name='read_num', shared_lock=SHARED_LOCK)
    write_num = UltraDict(name='write_num', shared_lock=SHARED_LOCK)
    
    while not Global['is_exit'] and active_cam[capture_id] != False:
        try:
            known_face_encodings = Global['known_face_encodings']
            known_face_names = Global['known_face_names']

            while (read_num[capture_id] != worker_id or read_num[capture_id] != prev_id(buff_num[capture_id], worker_num)) and not Global['is_exit']:
                time.sleep(0.01)


            # Read frame
            frame_process = read_frame_list[capture_id][worker_id]
            raw_frame = frame_process.copy()
            # Mark next worker to read frame
            read_num[capture_id] = next_id(read_num[capture_id], worker_num)

            # Process every 2 frames
            frames_since_last_process += 1
            if frames_since_last_process >= 5:
                frames_since_last_process = 0

                face_locations = face_recognition.face_locations(frame_process, model=config_dict["MODEL"])
                face_encodings = face_recognition.face_encodings(frame_process, face_locations)


            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                match_distance = face_recognition.face_distance(known_face_encodings, face_encoding)
                if len(match_distance) != 0:
                    minimum_distance = min(match_distance)
                else:
                    minimum_distance = 1
                name = "Unknown"
                if minimum_distance < config_dict["THRESHOLD"]:
                    for i in range(len(match_distance)):
                        if match_distance[i] == minimum_distance:
                            cur_time = datetime.now()
                            
                            
                            cur_encoding = known_face_encodings[i]

                            name = known_face_names[i]

                            if capture_id not in found_face_data:
                                found_face_data[capture_id] = {}
                            found_data = found_face_data[capture_id]
                            if name not in found_data or found_data[name] < cur_time.timestamp() - config_dict["DELAY_BEFORE_ADD_NEW_LOGS"]:
                                stream = io.BytesIO()
                                Image.fromarray(raw_frame).save(stream, format="JPEG")
                                imagebytes = stream.getvalue()
                                # Image.open(imagebytes).show()
                                if config_dict["USE_LINE_NOTIFY"] == True:
                                    noti = LineNotify(token=config_dict["LINE_NOTIFY_TOKEN"])
                                    noti.sendImage(imagebytes,f'FOUND "{name}" \nat camera "{capture_id}" \nTIME {cur_time.isoformat()}')
                                db.add_face_found_logs(name=name,encoding_in_frame=face_encoding,compared_encoding=cur_encoding,camera=capture_id,found_time=cur_time.isoformat(),image=imagebytes)
                            found_data[name] = cur_time.timestamp()
                            found_cam[capture_id] = found_data

                            break
                    
                cv2.rectangle(frame_process, (left, top), (right, bottom), config_dict["BOX_COLOR"], 2)
                cv2.putText(frame_process, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, config_dict["TEXT_COLOR"], 1)

            # Wait and write frame
            while write_num[capture_id] != worker_id:
                time.sleep(0.01)

            write_frame_list[capture_id][worker_id] = frame_process

            # Mark next worker to write frame
            write_num[capture_id] = next_id(write_num[capture_id], worker_num)

            del frame_process
        except TokenErrorException as e:
            messagebox.showwarning("Line Notify Token Error", "Please check your Line Notify Token")
        except Exception as e:
            messagebox.showerror("Error", e)
            print(e,"EXCEPTION")
    