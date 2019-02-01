import cv2
import tkinter as tk
import threading
import sys

#recording
window = None
recording = False
just_started = True

#tk ui
record_button = None
next_button = None
controls_button = None
about_button = None
credits_button = None
data_label = None
pop_up_window = None

#exp data
subjects = []
records_since_last_next = 0
current_subject = 0

#text
controls_text = '''
Space: start / stop recording
Enter: next sign / subject
Escape: quit
'''

about_text = '''
Version: 0.1
Developer: Jeffrey Sardina 

SignRecorder is a simple program for recording and saving 
video '.avi' files for sign language data collection and
experiments. It is currently hosted on GitHub
(https://github.com/Jeffrey-Sardina/SignRecorder)
as an open-source project.
'''

def main():
    load_data()
    init_gui()
    show_gui()

def load_data():
    try:
        with open('subjects.csv', 'r') as subject_data:
            for line in subject_data:
                name, sign_string = line.split(':')
                signs = sign_string.split(',')
                subjects.append(Subject(name, signs))
    except:
        subjects.append(Subject('No data found', ' '))

def init_gui():
    global window, record_button, data_label
    #layout / theming data
    padding_x = 10
    padding_y = 5
    backcolor = '#444444'
    color = '#777777'

    #Set up GUI
    window = tk.Tk()
    window.wm_title('Sign Recorder')
    window.config(background=backcolor)

    #input
    window.bind_all('<KeyRelease>', on_key_release)

    #Label
    data_label = tk.Label(window, text = 'Press Record or Next to get started', font = (None, 20), height = 3, width = 30, background = color)
    data_label.grid(row=0, column=0, padx=padding_x, pady=padding_y)

    #Buttons
    record_button = tk.Button(window, text ="Record", command = on_button_record, font = (None, 15), height = 3, width = 30, background = color)
    record_button.grid(row=1, column=0, padx=padding_x, pady=padding_y)

    next_button = tk.Button(window, text ="Next", command = on_button_next, font = (None, 15), height = 3, width = 30, background = color)
    next_button.grid(row=2, column=0, padx=padding_x, pady=padding_y)

    blank_label = tk.Label(window, text = '', font = (None, 20), height = 1, width = 30, background = backcolor)
    blank_label.grid(row=4, column=0, padx=padding_x, pady=padding_y)

    controls_button = tk.Button(window, text ="Controls", command = on_button_controls, font = (None, 15), height = 1, width = 30, background = color)
    controls_button.grid(row=5, column=0, padx=padding_x, pady=padding_y)

    about_button = tk.Button(window, text ="About", command = on_button_about, font = (None, 15), height = 1, width = 30, background = color)
    about_button.grid(row=6, column=0, padx=padding_x, pady=padding_y)

    blank_label2 = tk.Label(window, text = '', font = (None, 20), height = 1, width = 30, background = backcolor)
    blank_label2.grid(row=7, column=0, padx=padding_x, pady=padding_y)

    exit_button = tk.Button(window, text ="Exit", command = on_button_exit, font = (None, 15), height = 3, width = 30, background = color)
    exit_button.grid(row=8, column=0, padx=padding_x, pady=padding_y)

def show_gui():
    window.mainloop()

def on_key_release(event):
    if event.keysym == 'space':
        on_button_record()
    elif event.keysym == 'Return':
        on_button_next()
    elif event.keysym == 'Escape':
        on_button_exit()

def on_button_record():
    global recording, records_since_last_next, just_started
    if just_started:
        just_started = False
        on_button_next()
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
    global records_since_last_next, just_started
    records_since_last_next = 0
    if just_started:
        just_started = False
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
    global recording
    if recording:
        recording = False
    sys.exit()

def on_button_controls():
    global pop_up_window
    try:
        pop_up_window.destroy()
    except: #already closed by user, or never opened
        pass

    color = '#777777'

    pop_up_window = tk.Tk()
    pop_up_window.wm_title('Controls')
    pop_up_window.config(background=color)

    text = tk.Label(pop_up_window, text = controls_text, justify='left', font = (None, 20), height = 5, width = 30, background = color)
    text.grid(row=0, column=0, padx=10, pady=10)
    pop_up_window.mainloop()

def on_button_about():
    global pop_up_window
    try:
        pop_up_window.destroy()
    except: #already closed by user, or never opened
        pass

    color = '#777777'

    pop_up_window = tk.Tk()
    pop_up_window.wm_title('Controls')
    pop_up_window.config(background=color)

    text = tk.Label(pop_up_window, text = about_text, justify='left', font = (None, 20), height = 8, width = 50, background = color)
    text.grid(row=0, column=0, padx=10, pady=10)
    pop_up_window.mainloop()

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

main()