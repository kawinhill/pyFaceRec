import sqlite3
from datetime import datetime
import numpy as np
from UltraDict import UltraDict
from shared_lock import SHARED_LOCK
import pickle
from tkinter import messagebox
import os

def load_config():
    config_dict = {}
    if not os.path.exists("config.pkl"):
        print("config.pkl not found, creating new one")
        messagebox.showinfo("config.pkl not found", "config.pkl not found, creating new one")
        config_dict["LINE_NOTIFY_TOKEN"] = ""
        config_dict["USE_LINE_NOTIFY"] = False
        config_dict["DELAY_BEFORE_ADD_NEW_LOGS"] = 5
        config_dict["MODEL"] = "cnn"
        config_dict["THRESHOLD"] = 0.6
        config_dict["BOX_COLOR"] = (0,0,255)
        config_dict["TEXT_COLOR"] = (255,255,255)
        
        with open("config.pkl", "wb+") as f:
            pickle.dump(config_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
            
    config_dict = UltraDict(name="config",shared_lock=SHARED_LOCK,recurse=True)
    with open("config.pkl", "rb+") as f:
        config_dict_pk = pickle.load(f)
        for k,v in config_dict_pk.items():
            config_dict[k] = v
def save_config():
    config_dict = UltraDict(name="config",shared_lock=SHARED_LOCK,recurse=True)
    config_dict_save = {}
    for k,v in config_dict.items():
        config_dict_save[k] = v
    with open("config.pkl", "wb") as f:
        pickle.dump(config_dict_save, f, protocol=pickle.HIGHEST_PROTOCOL)
        

class Database:
    def __init__(self,filename="database.db"):
        self.conn = sqlite3.connect(filename, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS face_found_logs (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, encoding_in_frame BLOB, compared_encoding, camera TEXT, found_time TEXT, image BLOB)")
        self.conn.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS faces (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, encoding BLOB, image BLOB)")
        self.conn.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS camera (ID INTEGER PRIMARY KEY AUTOINCREMENT, camera TEXT)")
        self.conn.commit()
    def add_face_found_logs(self, name, encoding_in_frame, compared_encoding, camera,image, found_time=datetime.now().isoformat()):
        self.cursor.execute("INSERT INTO face_found_logs (name, encoding_in_frame, compared_encoding, camera, found_time, image) VALUES (?,?,?,?,?,?)", (name, encoding_in_frame, compared_encoding, camera, found_time, image))
        self.conn.commit()
    def add_camera(self, camera):
        self.cursor.execute("INSERT INTO camera (camera) VALUES (?)", (camera,))
        self.conn.commit()
    def get_camera(self):
        self.cursor.execute("SELECT * FROM camera")
        return self.cursor.fetchall()
    def get_face_found_logs(self):
        self.cursor.execute("SELECT * FROM face_found_logs")
        return self.cursor.fetchall()
    def add_face(self, name, encoding, image):
        self.cursor.execute("INSERT INTO faces (name, encoding, image) VALUES (?,?,?)", (name, encoding, image))
        self.conn.commit()
    def get_image_face(self, name, encoding):
        self.cursor.execute("SELECT image FROM faces WHERE name=? AND encoding=?", (name,encoding))
        return self.cursor.fetchall()[0][0]
    def get_faces(self):
        self.cursor.execute("SELECT * FROM faces")
        return self.cursor.fetchall()
    def get_face_split(self):
        data = self.get_faces()
        data_split = list(zip(*data))
        if len(data_split) < 3:
            return [], []    
        name, encoding = data_split[1], data_split[2]
        
        encodings = []
        for i in encoding:
            encodings.append(np.frombuffer(i))
        name = list(name)
        #encoding = list(encoding)
        return name, encodings
    def delete_camera(self, camera):
        self.cursor.execute("DELETE FROM camera WHERE camera=?", (camera,))
        self.conn.commit()
    def delete_face(self, name,encoding):
        self.cursor.execute("DELETE FROM faces WHERE name=? AND encoding=?", (name,encoding))
        self.conn.commit()
    
    def get_face_found_logs_split(self): #I don't know why I made this
        data = self.get_face_found_logs()
        data_split = list(zip(*data))
        name, encoding_in_frame, compared_encoding, camera, found_time = data_split
        name = list(name)
        encoding_in_frame = list(encoding_in_frame)
        compared_encoding = list(compared_encoding)
        camera = list(camera)
        found_time = list(found_time)
        return name, encoding_in_frame, compared_encoding, camera, found_time



