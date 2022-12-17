import os
import multiprocessing
import threading
import time


import tkinter
import face_recognition
from UltraDict import UltraDict
import processor as Processor
from capture import Camera, Media
from multiprocessor import MultiProcessingManager
from gui import *
from shared_lock import SHARED_LOCK
import database
import psutil

multiprocessing_manager = MultiProcessingManager()

is_tracking = False
class TaskBar(tkinter.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.start_track_button = tkinter.Button(self, text="Start Track", command=self.start_track)
        self.stop_track_button = tkinter.Button(self, text="Stop Track", command=self.stop_track)
        self.manage_cam_button = tkinter.Button(self, text="Manage Camera", command=self.manage_camera)
        self.manage_face = tkinter.Button(self, text="Manage Face", command=self.detector_manager)
        self.logs_button = tkinter.Button(self, text="Logs", command=self.logs_show)
        self.config_button = tkinter.Button(self, text="Config", command=self.config_manager)
        
        self.start_track_button.grid(row=0, column=0)
        self.stop_track_button.grid(row=0, column=1)
        self.manage_cam_button.grid(row=0, column=2)
        self.manage_face.grid(row=0, column=3)
        self.logs_button.grid(row=0, column=4)
        self.config_button.grid(row=0, column=5)
        
    def start_track(self):
        global is_tracking
        is_tracking = True
    def stop_track(self):
        global is_tracking
        is_tracking = False
    def manage_camera(self):
        ManageCameraPopup(self.master, multiprocessing_manager,feed_frame)
    def detector_manager(self):
        ManageFacePopup(self.master, multiprocessing_manager,feed_frame)
    def logs_show(self):
        LogsFrame(self.master, multiprocessing_manager)
    def config_manager(self):
        ConfigFrame(self.master)

def main(window, feed_frame):
    
    database.load_config()
    
    db = database.Database()

    captures = []
    for db_cam in db.get_camera():
        captures.append(Media(db_cam[1],multiprocessing_manager))
    # captures = [
    #     #Camera(0, multiprocessing_manager),
        
    #     Media("videos/fpaHA8TKz5Y.mp4", multiprocessing_manager),
    #     Media("videos/YF248uEezjI.mp4", multiprocessing_manager),
    #     #Media("videos/XkZrDvv0798.mp4", multiprocessing_manager),
    #     #Media("videos/MPywGQPLJPo.mp4", multiprocessing_manager),
    #     #Media("videos/AkgB6fvbri4.mp4", multiprocessing_manager),
    #     #test
        
    #     # ウェザーニュース LiveTV
    #     # Media("http://movie.mcas.jp/mcas/wn1_2/master.m3u8", multiprocessing_manager),
        
    #     # 日本购物1 LiveTV (มีแต่ขายของ 55555555555)
    #     # Media("http://stream1.shopch.jp/HLS/out1/prog_index.m3u8", multiprocessing_manager)
    # ]

    for capture in captures:
        multiprocessing_manager.new_capture(capture)
        feed_frame.add(capture)

    feed_frame.show([c.get_id() for c in captures])


    
    name, encoding = db.get_face_split()
    multiprocessing_manager.Global['known_face_encodings'] = encoding
    multiprocessing_manager.Global['known_face_names'] = name
            
    print("Known faces:", multiprocessing_manager.Global['known_face_names'])

    # Wait 1s before starting the next worker, so it won't overload
    # (The freezing that happens when you start the program)
    DELAY_START = 1 
    # Start processing
    for worker_id in range(1, multiprocessing_manager.worker_num + 1):
        for capture in captures:
            p = multiprocessing.Process(target=Processor.process, args=(capture.id, worker_id, multiprocessing_manager.worker_num))
            multiprocessing_manager.process.append(p)
            p.start()
            time.sleep(DELAY_START)
            print(f"Started worker {worker_id} for {capture.id}")

    # feed_frame.show([c.get_id() for c in captures])
    feed_frame.show_all()


def tracking_frame_thread():
    global is_tracking
    found_cam = UltraDict(name='found_cam', shared_lock=SHARED_LOCK)
    
    while True:
        if is_tracking:
            x = []
            for i in found_cam.keys():
                for j in found_cam[i].keys():
                    if found_cam[i][j]+5 > time.time():
                        x.append(i)
                        break
                    
            x.sort()
            y = feed_frame.get_showing()
            if x != y:
                feed_frame.show(x)
            print("Tracking")
            time.sleep(1)
        else:
            feed_frame.show_all()
            while not is_tracking:
                time.sleep(1)


def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        p = psutil.Process(os.getpid())
        for c in p.children(recursive=True):
            c.kill()
        os._exit(0)
        # window.destroy()
        

if __name__ == '__main__':
    window = tkinter.Tk()
    window.state('zoomed')
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.title("Face Recognition")
    x = TaskBar(window)
    x.pack()
    feed_frame = FeedManagerFrame(window)
    feed_frame.pack()
    
    t = threading.Thread(target=main, args=(window, feed_frame,))
    t.start()
    tr = threading.Thread(target=tracking_frame_thread)
    tr.start()
    
    window.mainloop()
    