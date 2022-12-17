import time
import subprocess
import numpy

import cv2

from multiprocessor import next_id, prev_id
from UltraDict import UltraDict

from shared_lock import SHARED_LOCK

NO_FEED = cv2.cvtColor(cv2.imread('NOFEED.png'), cv2.COLOR_BGR2RGB)

class FFmpegCapture:
    def __init__(self, stream, width=640, height=360, scale=1, fps=30):
        self.command = 'ffmpeg -hide_banner -loglevel error -i {i} -f rawvideo -pix_fmt bgr24 -s {w}x{h} -r {fps} -'
        self.stream = stream
        self.width = width
        self.height = height
        self.scale = scale
        self.fps = fps

        self.errors = []
        self.start()

    def start(self):
        width = int(self.width * self.scale)
        height = int(self.height * self.scale)
        command = self.command.format(i=self.stream, w=width, h=height, fps=self.fps)
        self.capture = subprocess.Popen(command.split(' '), stdout= subprocess.PIPE, bufsize=10 ** 8)

    def read(self):
        buffer = self.capture.stdout.read(self.width * self.height * 3)

        # Break the loop if buffer length is not W*H*3 (when FFmpeg streaming ends).
        if len(buffer) != self.width * self.height * 3:
            return False, NO_FEED
        
        frame = numpy.frombuffer(buffer, numpy.uint8).reshape(self.height, self.width, 3)
        return frame is not None, frame
    
    def get(self, value):
        # 4 - Height
        # 3 - Width
        # 5 - FPS
        if value == 4:
            return self.height
        if value == 3:
            return self.width
        if value == 5:
            return self.fps
        else:
            raise NotImplementedError("Not implemented")
    def release(self):
        self.__exit__(None, None, None)
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.capture.terminate()

class VideoCapture:
    def __init__(self, id, multiprocessing_manager) -> None:
        self.id = id
        self.capture = None
        self.latest_frame = NO_FEED

        self.multiprocessing_manager = multiprocessing_manager
    def get_id(self):
        return self.id
    def start(self):
        print(f"[{type(self).__name__} VideoCapture #{str(self.id)[:20]} Height: {self.capture.get(4)}, Width: {self.capture.get(3)}, FPS: {self.capture.get(5)}")
        read_frame_list = UltraDict(name='read_frame_list')
        buff_num = UltraDict(name='buff_num', shared_lock=SHARED_LOCK)
        read_num = UltraDict(name='read_num', shared_lock=SHARED_LOCK)
        
        while not self.multiprocessing_manager.Global['is_exit'] and self.multiprocessing_manager.active_cam[self.id]:
            
            
            if buff_num[self.id] != next_id(read_num[self.id], self.multiprocessing_manager.worker_num):
                ret, frame = self.capture.read()
                if frame is None:
                    buff_num[self.id] = next_id(buff_num[self.id], self.multiprocessing_manager.worker_num)
                    read_frame_list[self.id][buff_num[self.id]] = NO_FEED
                    continue
                
                # If frame is bigger than 480p, rescale it down to near 480p keeping aspect ratio
                downscale_target_width, downscale_target_height = 848, 480
                if frame.shape[1] > downscale_target_width or frame.shape[0] > downscale_target_height:
                    scale = 1
                    while frame.shape[1] / scale > downscale_target_width or frame.shape[0] / scale > downscale_target_height:
                        scale += 1
                    frame = cv2.resize(frame, (int(frame.shape[1] / scale), int(frame.shape[0] / scale)))
    
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                read_frame_list[self.id][buff_num[self.id]] = frame
                buff_num[self.id] = next_id(buff_num[self.id], self.multiprocessing_manager.worker_num)
                del frame
            else:
                time.sleep(0.01)

        self.capture.release()
        
    def update(self):
        last_num = 1
        fps_list = []
        tmp_time = time.time()
        
        write_frame_list  = UltraDict(name='write_frame_list')
        write_num = UltraDict(name='write_num', shared_lock=SHARED_LOCK)
        
        while not self.multiprocessing_manager.Global['is_exit'] and self.multiprocessing_manager.active_cam[self.id]:
            try:
                while write_num[self.id] != last_num:
                    last_num = write_num[self.id]


                    delay = time.time() - tmp_time
                    tmp_time = time.time()
                    fps_list.append(delay)
                    
                    if len(fps_list) > 5 * self.multiprocessing_manager.worker_num:
                        fps_list.pop(0)
                    
                    fps = len(fps_list) / numpy.sum(fps_list)

                    self.multiprocessing_manager.Global['frame_delay'] = 0
                    try:
                        self.latest_frame = write_frame_list[self.id][write_num[self.id]]
                    except Exception as err:
                        self.latest_frame = NO_FEED
                        print(f"[{type(self).__name__} VideoCapture #{str(self.id)[:20]}] Unable to process frame, ", err)
                
                time.sleep(0.01)
            except:
                pass
      
    def get_latest_frame(self):
        return self.latest_frame
    
class Camera(VideoCapture):
    def __init__(self, id, multiprocessing_manager):
        super().__init__(id, multiprocessing_manager)
        self.capture = cv2.VideoCapture(self.id)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 4)

class Media(VideoCapture):
    def __init__(self, id, multiprocessing_manager):
        super().__init__(id, multiprocessing_manager)
        self.capture = FFmpegCapture(self.id)