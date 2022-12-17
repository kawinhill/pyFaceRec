import threading
from tkinter import filedialog
import tkinter
from tkinter import messagebox,colorchooser
from tkinter import ttk
import face_recognition
import io
import multiprocessing
from capture import Camera, Media
from PIL import Image, ImageTk
import cv2
from capture import VideoCapture
import database
import numpy as np
from UltraDict import UltraDict
import processor as Processor
from shared_lock import SHARED_LOCK

class WrongInputError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
    def __str__(self):
        return f"Error Wrong Input - \"{self.message}\" is not a valid input"

class NoCameraError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
    def __str__(self):
        return f"Error No Camera - \"{self.message}\" is not a valid camera"
    
class TkCaptureFrame(tkinter.Frame):  
    def __init__(self, window, capture):
        super().__init__(window)
        self.capture = capture
        self.create_widgets()
    def create_widgets(self):
        # Don't ask me why tf I use label, it's the fastest one to render the image
        # No idea why canvas sucks and LABEL is the best?!??!?
        self.panel = tkinter.Label(self, width=640, height=480, anchor=tkinter.NW)
        self.panel.pack()
        self.update_thread = threading.Thread(target=self.update, args=())
        self.update_thread.start()

    def update(self):
        imgtk = ImageTk.PhotoImage(image=Image.fromarray(self.capture.get_latest_frame()))
        self.panel.imgtk = imgtk
        self.panel.config(image=imgtk)
        self.panel.update()
        self.after(10, self.update)
        
    def __delattr__(self, __name: str) -> None:
        del self.cam
        super().__delattr__(__name)

class ManageCameraPopup(tkinter.Toplevel):
    def __init__(self, window, multiprocessing_manager,feed_frame):
        super().__init__(window)
        self.multiprocessing_manager = multiprocessing_manager
        self.feed_frame = feed_frame
        self.create_widgets()
        
    def create_widgets(self):
        self.frame = tkinter.Frame(self)
        self.frame.pack()
        self.listbox = tkinter.Listbox(self.frame)
        self.listbox.pack()
        self.refresh()
        self.button = tkinter.Button(self, text='Exit', command=self.exit)
        self.button.pack()
        self.test_bt = tkinter.Button(self, text='Delete', command=self.delete_selected)
        self.test_bt.pack()
        self.add_bt = tkinter.Button(self, text='Add', command=self.add_camera_popup)
        self.add_bt.pack()
        
    
    def refresh(self):
        self.listbox.delete(0, tkinter.END)
        for camera_id in self.multiprocessing_manager.active_cam.keys():
            if self.multiprocessing_manager.active_cam[camera_id]:
                self.listbox.insert(tkinter.END, camera_id)
    def add_camera_popup(self):
        try:
            result = TextInputPopup(self).show()
            cap = cv2.VideoCapture(result)
            self.add_camera(result)
            # return
            if cap.isOpened():
                self.multiprocessing_manager.active_cam[result] = True
                cap.release()
                self.add_camera(result)            
                
                messagebox.showinfo("Success", "Camera added")
            else:
                
                raise NoCameraError(result)
            
        except WrongInputError as e:
            messagebox.showwarning("Warning", e)
        except NoCameraError as e:
            messagebox.showwarning("Warning", e)
        except Exception as e:
            messagebox.showerror("Error", e)
        
        
    def add_camera(self,cam_id):
        capture = Media(cam_id, self.multiprocessing_manager)
        db = database.Database()
        db.add_camera(cam_id)
        self.multiprocessing_manager.new_capture(capture)
        self.feed_frame.add(capture)
        self.feed_frame.show_all()
        for worker_id in range(1, self.multiprocessing_manager.worker_num + 1):
            p = multiprocessing.Process(target=Processor.process, args=(capture.id, worker_id, self.multiprocessing_manager.worker_num))
            self.multiprocessing_manager.process.append(p)
            p.start()
            print(f"Started worker {worker_id} for {capture.id}")
        self.refresh()
    def delete_selected(self):
        selected = self.listbox.get(self.listbox.curselection())
        self.listbox.delete(self.listbox.curselection())
        self.multiprocessing_manager.active_cam[selected] = False

        db = database.Database()
        db.delete_camera(selected)
        self.feed_frame.remove(selected)
        self.feed_frame.show_all()
    def exit(self):
        self.destroy()
        
    def __delattr__(self, __name: str) -> None:
        super().__delattr__(__name)

class TextInputPopup(tkinter.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.var = tkinter.StringVar()
        label = tkinter.Label(self, text="Enter Camera Source:")
        self.entry = tkinter.Entry(self, textvariable=self.var)
        button = tkinter.Button(self, text="OK", command=self.destroy)
        label.pack(side="top", fill="x")
        self.entry.pack(side="top", fill="x")
        button.pack()

    def show(self):
        self.deiconify()
        self.wait_window()
        value = self.var.get()
        if value == "":
            raise WrongInputError("No input")
        return value
class ManageFacePopup(tkinter.Toplevel):
    def __init__(self, window, multiprocessing_manager,feed_frame):
        super().__init__(window)
        self.title("Manage Face")
        self.grab_set()
        self.image_list = []
        self.multiprocessing_manager = multiprocessing_manager
        self.feed_frame = feed_frame
        self.create_widgets()
        Global = UltraDict(name='global', shared_lock=SHARED_LOCK)
    def create_widgets(self):
        self.frame = tkinter.Frame(self)
        self.frame.pack()
        self.listbox = tkinter.Listbox(self.frame)
        self.listbox.bind("<Double-1>", self.OnDoubleClick)
        self.listbox.pack()
        self.refresh()
        self.button = tkinter.Button(self, text='Exit', command=self.exit)
        self.button.pack()
        self.test_bt = tkinter.Button(self, text='Delete', command=self.delete_selected)
        self.test_bt.pack()
        self.add_face_bt = tkinter.Button(self, text='Add Face', command=self.add_face)
        self.add_face_bt.pack()
    def OnDoubleClick(self, event):
        item = self.listbox.curselection()[0]

        img = self.image_list[item]
        ShowImage(self, img)
    def refresh(self):
        self.listbox.delete(0, tkinter.END)
        self.image_list = []
        db = database.Database()
        Global = UltraDict(name='global', shared_lock=SHARED_LOCK)
        for face_name,face_encoding in zip(Global['known_face_names'],Global['known_face_encodings']):
            self.image_list.append(db.get_image_face(face_name, face_encoding))
            # print(self.image_list)
            self.listbox.insert(tkinter.END, face_name)
    def add_face(self):
        known_face_encodings = self.multiprocessing_manager.Global['known_face_encodings']
        known_face_names = self.multiprocessing_manager.Global['known_face_names']
        path = filedialog.askopenfilename()
        name = path.split('/')[-1].split('.')[0]
        try:
            img = face_recognition.load_image_file(path)
            stream = io.BytesIO()
            im = Image.fromarray(img)
            im.verify()
            im.save(stream, format="JPEG")
        except Exception:
            messagebox.showwarning("Image Error","Please Check image file")
        
        imagebytes = stream.getvalue()
        img_face = face_recognition.face_encodings(img)
        if len(img_face) == 0:
            messagebox.showwarning("Error", "No face detected")
            return
        known_face_encodings.append(img_face[0])
        known_face_names.append(name)
        db = database.Database()
        db.add_face(name, face_recognition.face_encodings(img)[0],imagebytes)
        self.multiprocessing_manager.Global['known_face_encodings'] = known_face_encodings
        self.multiprocessing_manager.Global['known_face_names'] = known_face_names
        self.refresh()
    def delete_selected(self):
        Global = UltraDict(name='global', shared_lock=SHARED_LOCK)
        selected = self.listbox.get(self.listbox.curselection())
        new_name = Global['known_face_names'].copy()
        new_encoding = Global['known_face_encodings'].copy()
        with Global.lock:
            enc = new_encoding.pop(self.listbox.curselection()[0])
            name = new_name.pop(self.listbox.curselection()[0])
            db = database.Database()
            db.delete_face(name,enc)
            Global['known_face_names'] = new_name
            Global['known_face_encodings'] = new_encoding
        self.refresh()
    def exit(self):
        self.destroy()
        
    def __delattr__(self, __name: str) -> None:
        super().__delattr__(__name)
        

class FeedManagerFrame(tkinter.Frame):
    def __init__(self, window):
        super().__init__(window)
        self.captures = {}
        self.frame = tkinter.Frame(self)
    
    def add(self, capture: VideoCapture):
        self.captures[capture.get_id()] = TkCaptureFrame(self, capture)
    
    def remove(self, capture):
        self.captures[capture].grid_forget()
        del self.captures[capture]
    def get_showing(self):
        temp = list(self.captures.keys()) + []
        ret = [capture for capture in temp if self.captures[capture].winfo_ismapped()]
        ret.sort()
        return ret
    def show_all(self):
        self.show(self.captures.keys())
    def show(self, capture_list):
        row = 0
        col = 0
        for capture in self.captures.keys():
            if capture in capture_list:
                self.captures[capture].grid(row=row, column=col)
                col += 1
                if col == 3:
                    row += 1
                    col = 0
            else:
                self.captures[capture].grid_forget()

        self.frame.grid(row=0, column=0)
        
class ShowImage(tkinter.Toplevel):
    def __init__(self, window, image):
        super().__init__(window)
        self.grab_set()
        self.title("ShowImage")
        self.image = image
        self.create_widgets()
    def create_widgets(self):
        self.frame = tkinter.Frame(self)
        self.frame.pack()
        self.img = Image.open(io.BytesIO(self.image))
        self.imgtk = ImageTk.PhotoImage(image=self.img)
        self.image_label = tkinter.Label(self.frame, image=self.imgtk)
        self.image_label.pack()
        self.button = tkinter.Button(self.frame, text='Exit', command=self.exit)
        self.button.pack()
    def exit(self):
        self.destroy()
        self.update()

        


class ConfigFrame(tkinter.Toplevel):
    def __init__(self, window):
        super().__init__(window)
        self.title("Config")
        self.grab_set()
        self.create_widgets()
    def create_widgets(self):
        self.frame = tkinter.Frame(self)
        self.frame.pack()
        
        self.token_label = tkinter.Label(self.frame, text="Token")
        self.token_label.grid(row=0, column=0)
        self.token_var = tkinter.StringVar()
        self.token_entry = tkinter.Entry(self.frame, textvariable=self.token_var)
        self.token_entry.grid(row=0, column=1)
        
        self.use_line_label = tkinter.Label(self.frame, text="Use Line Notify")
        self.use_line_label.grid(row=1, column=0)
        self.use_line_var = tkinter.BooleanVar()
        self.use_line_entry = tkinter.Checkbutton(self.frame, variable=self.use_line_var, onvalue=True, offvalue=False)
        self.use_line_entry.grid(row=1, column=1)
        
        self.choose_model_label = tkinter.Label(self.frame, text="Face Detection Model")
        self.choose_model_label.grid(row=2, column=0)
        self.choose_model_var = tkinter.StringVar()
        self.choose_model_frame = tkinter.Frame(self.frame)
        self.choose_model_frame.grid(row=2, column=1)
        self.choose_model_cnn = tkinter.Radiobutton(self.choose_model_frame, text="CNN", variable=self.choose_model_var, value="cnn")
        self.choose_model_hog = tkinter.Radiobutton(self.choose_model_frame, text="HOG", variable=self.choose_model_var, value="hog")
        self.choose_model_cnn.grid(row=0, column=0)
        self.choose_model_hog.grid(row=0, column=1)
        
        self.logs_delay_label = tkinter.Label(self.frame, text="Logs Delay")
        self.logs_delay_label.grid(row=3, column=0)
        self.logs_delay_var = tkinter.IntVar()
        self.logs_delay_entry = tkinter.Entry(self.frame, textvariable=self.logs_delay_var,validate="key", validatecommand=(self.register(self.validate_int), '%P'))
        self.logs_delay_entry.grid(row=3, column=1)
        
        self.threshold_label = tkinter.Label(self.frame, text="Threshold")
        self.threshold_label.grid(row=4, column=0)
        self.threshold_var = tkinter.DoubleVar()
        self.threshold_entry = tkinter.Entry(self.frame, textvariable=self.threshold_var,validate="key", validatecommand=(self.register(self.validate_float), '%P'))
        self.threshold_entry.grid(row=4, column=1)
        
        self.box_color_label = tkinter.Label(self.frame, text="Box Color")
        self.box_color_label.grid(row=5, column=0)
        self.box_color_button = tkinter.Button(self.frame, text="Choose Box Color", command=self.choose_box_color)
        self.box_color_button.grid(row=5, column=1)
        
        self.text_color_label = tkinter.Label(self.frame, text="Text Color")
        self.text_color_label.grid(row=6, column=0)
        self.text_color_button = tkinter.Button(self.frame, text="Choose Text Color", command=self.choose_text_color)
        self.text_color_button.grid(row=6, column=1)
        
        self.reset_button = tkinter.Button(self.frame, text='Reset', command=self.reset_config)
        self.reset_button.grid(row=7, column=0)
        self.save_button = tkinter.Button(self.frame, text='Save and Exit', command=self.save_config)
        self.save_button.grid(row=8, column=0)
        self.exit_button = tkinter.Button(self.frame, text='Exit', command=self.exit)
        self.exit_button.grid(row=8, column=1)
        self.load_config()
    def reset_config(self):
        self.token_var.set("")
        self.use_line_var.set(False)
        self.choose_model_var.set("cnn")
        self.logs_delay_var.set(5)
        self.threshold_var.set(0.6)
        self.box_color = (0,0,255)
        self.text_color = (255,255,255)
    def choose_box_color(self):
        color = colorchooser.askcolor(initialcolor=self.box_color)
        if color[1]:
            self.box_color = color[0]
    def choose_text_color(self):
        color = colorchooser.askcolor(initialcolor=self.text_color)
        if color[1]:
            self.text_color = color[0]
    def save_config(self):
        config_dict = UltraDict(name="config",shared_lock=SHARED_LOCK,recurse=True)
        config_dict["LINE_NOTIFY_TOKEN"] = self.token_var.get()
        config_dict["USE_LINE_NOTIFY"] = self.use_line_var.get()
        config_dict["LOGS_DELAY"] = self.logs_delay_var.get()
        config_dict["MODEL"] = self.choose_model_var.get()
        config_dict["THRESHOLD"] = self.threshold_var.get()
        config_dict["BOX_COLOR"] = self.box_color
        config_dict["TEXT_COLOR"] = self.text_color
        
        # self.print_config()
        database.save_config()
        self.exit()
        messagebox.showinfo("Success", "Config saved")
        
    def exit(self):
        self.destroy()
        self.update()
    def load_config(self):
        config_dict = UltraDict(name="config",shared_lock=SHARED_LOCK,recurse=True)
        self.token_var.set(config_dict["LINE_NOTIFY_TOKEN"])
        self.use_line_var.set(config_dict["USE_LINE_NOTIFY"])
        self.logs_delay_var.set(config_dict["DELAY_BEFORE_ADD_NEW_LOGS"])
        self.choose_model_var.set(config_dict["MODEL"])
        self.threshold_var.set(config_dict["THRESHOLD"])
        self.box_color = config_dict["BOX_COLOR"]
        self.text_color = config_dict["TEXT_COLOR"]
        
    def print_config(self):
        print("Token: ", self.token_var.get())
        print("Use Line Notify: ", self.use_line_var.get())
        print("Logs Delay: ", self.logs_delay_var.get())
        print("Model: ", self.choose_model_var.get())
        print("Threshold: ", self.threshold_var.get())
        
    def validate_int(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False
    def validate_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False
class LogsFrame(tkinter.Toplevel):
    def __init__(self, window, multiprocessing_manager):
        super().__init__(window)
        self.grab_set()
        self.create_widgets()
    def create_widgets(self):
        self.frame = tkinter.Frame(self)
        self.frame.pack()
        columns = ('Time', 'Name', 'Camera')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings')
        self.tree.heading('Time', text='Time')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Camera', text='Camera')
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tkinter.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.tree.bind("<Double-1>", self.OnDoubleClick)
        self.refresh()
        self.refresh_bt = tkinter.Button(self.frame, text='Refresh', command=self.refresh)
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.refresh_bt.grid(row=1, column=0, sticky='nsew')
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        db = database.Database()
        data = db.get_face_found_logs()
        self.image_list = []
        for row in data:
            self.tree.insert('', 0, values=(row[5],row[1],row[4]))
            self.image_list.insert(0,row[6])#
        self.tree.yview_moveto(0)
    def OnDoubleClick(self, event):
        item = self.tree.selection()[0] #6
        img = self.image_list[self.tree.index(item)]
        
        ShowImage(self, img)

