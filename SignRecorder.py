import cv2
import numpy
import tkinter as tk
from PIL import Image, ImageTk
import threading

#recording
window = None
recording = False

#ui
record_button = None
next_button = None
data_label = None

#exp data
subjects = []
records_since_last_next = 0
current_subject = 0

class Subject():
    name = 'un-named'
    signs = []
    current_sign = -1

    def __init__(self, s_name, s_signs):
        self.name = s_name
        self.signs = s_signs

    def next_sign(self):
        self.current_sign += 1
        if self.current_sign < len(self.signs):
            sign = self.signs[self.current_sign].strip()
            return sign
        else:
            return None

    def current_sign_value(self):
        if self.current_sign < len(self.signs):
            return self.signs[self.current_sign].strip()
        else:
            return 'None'

def main():
    load_data()
    init_gui()
    show_gui()

def load_data():
    with open('subjects.csv', 'r') as subject_data:
        for line in subject_data:
            name, sign_string = line.split(':')
            signs = sign_string.split(',')
            subjects.append(Subject(name, signs))

def init_gui():
    global opencv_image_label, window, record_button, data_label
    #Set up GUI
    window = tk.Tk()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window.wm_title('Sign Recorder')
    window.config(background='#444444')

    #input
    window.bind_all('<KeyRelease>', on_key_release)

    #Graphics window
    opencv_image_frame = tk.Frame(window, width=screen_width, height=screen_height)
    opencv_image_frame.grid(row=0, column=0, padx=10, pady=2)

    #Capture video frames
    opencv_image_label = tk.Label(opencv_image_frame)
    opencv_image_label.grid(row=0, column=0)

    padding_x = 10
    padding_y = 5
    color = '#777777'

    #Label
    data_label = tk.Label(window, text = 'Press Next to get started', font = (None, 20), height = 3, width = 30, background = color)
    data_label.grid(row=0, column=0, padx=padding_x, pady=padding_y)

    #Buttons
    record_button = tk.Button(window, text ="Record", command = on_button_record, font = (None, 15), height = 3, width = 30, background = color)
    record_button.grid(row=1, column=0, padx=padding_x, pady=padding_y)

    next_button = tk.Button(window, text ="Next", command = on_button_next, font = (None, 15), height = 3, width = 30, background = color)
    next_button.grid(row=2, column=0, padx=padding_x, pady=padding_y)

    exit_button = tk.Button(window, text ="Exit", command = on_button_exit, font = (None, 15), height = 3, width = 30, background = color)
    exit_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)

def show_gui():
    window.mainloop()

def on_key_release(event):
    if event.keysym == 'space':
        on_button_record()
    elif event.keysym == 'Return':
        on_button_next()
    elif event.keysym == 'Escape':
        on_button_exit()

class Recorder(threading.Thread):
    name = ''
    fps = 0
    mirror = False

    def __init__(self, name, fps, mirror):
        threading.Thread.__init__(self)
        self.name = name
        self.fps = fps
        self.mirror = mirror

    def run(self):
        # Capturing video from webcam:
        web_cam = cv2.VideoCapture(0)

        currentFrame = 0

        #get width and height of reading frame
        width = int(web_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(web_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        video_writer= cv2.VideoWriter(self.name + '.avi', fourcc, self.fps, (width, height))
    
        while web_cam.isOpened():
    
            # Capture frame-by-frame
            is_reading, frame = web_cam.read()
    
            if is_reading and recording:
                if self.mirror:
                    # Mirror the if needed
                    frame = cv2.flip(frame, 1)

                # Saves for video
                video_writer.write(frame)
    
                # Display the resulting frame
                cv2.imshow('frame', frame)
            else:
                break
    
            if cv2.waitKey(1) & 0xFF == ord(' '): #quit on space
                on_button_record()
                break
    
            # To stop duplicate images
            currentFrame += 1
    
        # When everything done, release the capture
        web_cam.release()
        video_writer.release()
        cv2.destroyAllWindows()

def on_button_record():
    global recording, records_since_last_next
    if recording:
        recording = False
        record_button.config(text = 'Record')
    else:
        recording = True
        records_since_last_next += 1
        record_button.config(text = 'Stop')
        name = subjects[current_subject].name
        sign = subjects[current_subject].current_sign_value()
        data_label.config(text = name + '; ' + sign)
        Recorder(name + ' ' + sign + '--Try' + str(records_since_last_next), 30, True).start()

def on_button_next():
    global records_since_last_next
    records_since_last_next = 0
    if recording:
        on_button_record()
    next_sign_or_subject()

def next_sign_or_subject():
    global current_subject, data_label
    if not current_subject >= len(subjects):
        subject = subjects[current_subject]
        name = subject.name
        sign = subject.next_sign()
    else:
        name = ''
        sign = None
        
    if sign == None:
        current_subject += 1
        if current_subject >= len(subjects):
            data_label.config(text = 'All data collected')
        else:
            name = subjects[current_subject].name
            sign = subjects[current_subject].next_sign()
            data_label.config(text = name + '; ' + sign)
    else:
        data_label.config(text = name + '; ' + sign)

def on_button_exit():
    exit()

main()