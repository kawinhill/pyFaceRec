import threading
from UltraDict import UltraDict

from shared_lock import SHARED_LOCK

class MultiProcessingManager():
    def __init__(self) -> None:
        self.Global = UltraDict(name='global', recurse=True, shared_lock=SHARED_LOCK, auto_unlink=True, buffer_size=10000000, full_dump_size=10000000)
        self.active_cam = UltraDict(name='active_cam', shared_lock=SHARED_LOCK)
        self.buff_num = UltraDict(name='buff_num', shared_lock=SHARED_LOCK, auto_unlink=True, buffer_size=10000000, full_dump_size=10000000)
        self.read_num = UltraDict(name='read_num', shared_lock=SHARED_LOCK, auto_unlink=True, buffer_size=10000000, full_dump_size=10000000)
        self.write_num = UltraDict(name='write_num', shared_lock=SHARED_LOCK, auto_unlink=True, buffer_size=10000000, full_dump_size=10000000)
        self.Global['frame_delay'] = 0
        self.Global['is_exit'] = False
        
        
        #offset = 0
        self.worker_num = 2
        self.process = []
        
        # 15MB buffer per worker
        BUFFER_SIZE_PER_WORKER = 15_000_000
        self.read_frame_list = UltraDict(name='read_frame_list', recurse=True, auto_unlink=True, buffer_size=self.worker_num * BUFFER_SIZE_PER_WORKER, full_dump_size=self.worker_num * BUFFER_SIZE_PER_WORKER, shared_lock=SHARED_LOCK)
        self.write_frame_list = UltraDict(name='write_frame_list', recurse=True, auto_unlink=True, buffer_size=self.worker_num * BUFFER_SIZE_PER_WORKER, full_dump_size=self.worker_num * BUFFER_SIZE_PER_WORKER, shared_lock=SHARED_LOCK)
        
    def new_capture(self, capture):

        self.active_cam[capture.get_id()] = True
        self.buff_num[capture.id] = 1
        self.read_num[capture.id] = 1
        self.write_num[capture.id] = 1
        
        self.read_frame_list[capture.id] = {}
        self.write_frame_list[capture.id] = {}
        
        p = threading.Thread(target=capture.start, daemon=True)
        p.start()
        self.process.append(p)
        
        p2 = threading.Thread(target=capture.update, daemon=True)
        p2.start()
        self.process.append(p)

def next_id(current_id, worker_num):
    if current_id == worker_num:
        return 1
    else:
        return current_id + 1

def prev_id(current_id, worker_num):
    if current_id == 1:
        return worker_num
    else:
        return current_id - 1