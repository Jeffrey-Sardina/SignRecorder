import cv2
import tkinter as tk
import threading
import sys
import logging
import os
import imghdr

#backend
logger = None
settings = None

#data
webcam_num = 0

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
Enter: next stimulus / subject
Escape: quit
'''

about_text = '''
Version: 0.1
Developer: Jeffrey Sardina 

SignRecorder is a simple program for recording and saving 
video '.avi' files for stimulus language data collection and
experiments. It is currently hosted on GitHub
(https://github.com/Jeffrey-Sardina/SignRecorder)
as an open-source project.
'''

def main():
    init_logging()
    find_webcams(10)
    init_config()
    load_data()
    init_gui()
    #Image_Displayer(os.path.abspath('test.jpg'), 1000).start()
    #Image_Displayer(os.path.abspath('test2.jpg'), 1000).start()
    #Video_Displayer(os.path.abspath('test.avi')).start()
    show_gui()

def init_logging():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('SignRecorder.log', mode='w')
    logger.addHandler(file_handler)
    file_handler_format = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
    file_handler.setFormatter(file_handler_format)
    logger.info('Starting log')

def find_webcams(search_num):
    global webcam_num
    for i in range(search_num):
        webcam_i = cv2.VideoCapture(i)
        if webcam_i.isOpened():
            webcam_num += 1
            webcam_i.release()
    if webcam_num == 0:
        logger.critical('No cameras found for recording!')

def init_config():
    global settings
    settings = Settings()

def load_data():
    try:
        with open('subjects.csv', 'r') as subject_data:
            for line in subject_data:
                name, sign_string = line.split(':')
                stimuli = sign_string.split(',')
                subjects.append(Subject(name, stimuli))
    except Exception as err:
        logger.warning('No experiment data found: ' + str(err))
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

def on_key_down(event):
    if event.keysym == 'space':
        pass
    elif event.keysym == 'Return':
        pass
    elif event.keysym == 'Escape':
        pass

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
        stimulus, stimulus_type = subjects[current_subject].current_stimulus_value()
        data_label.config(text = name + '; ' + stimulus)
        Recorder(name + ' ' + stimulus + '--Try' + str(records_since_last_next), 30, True).start()

def on_button_next():
    global records_since_last_next, just_started
    records_since_last_next = 0
    if just_started:
        just_started = False
    if recording:
        on_button_record()
    next_stimulus_or_subject()

def next_stimulus_or_subject():
    global current_subject, data_label
    if not current_subject >= len(subjects):
        subject = subjects[current_subject]
        name = subject.name
        stimulus, stimulus_type = subject.next_stimulus()
    else:
        name = ''
        stimulus = None
        
    if stimulus == None:
        current_subject += 1
        if current_subject >= len(subjects):
            data_label.config(text = 'All data collected')
        else:
            name = subjects[current_subject].name
            stimulus, stimulus_type = subjects[current_subject].next_stimulus()
            data_label.config(text = name + '; ' + stimulus)
    else:
        data_label.config(text = name + '; ' + stimulus)

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

class Settings():
    cam_num = 0
    display_cam_feed = False
    allow_override = False

    def __init__(self):
        self.load_config()

    def load_config(self):
        try:
            with open('config.csv', 'r') as config:
                for line in config:
                    key, value = line.split(',', 1)
                    if key == 'cam_num':
                        self.cam_num = int(value)
                    if key == 'display_cam_feed':
                        self.display_cam_feed = int(value) == 1
                    if key == 'allow_override':
                        self.allow_override = int(value) == 1
        except Exception as err:
            logger.error('Settings.load_config: could not read config file: ' + str(err))

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

        #get width and height of reading frame
        width = int(web_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(web_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
        # Define the codec and 
        fourcc = cv2.VideoWriter_fourcc(*"XVID")

        #create VideoWriter object
        file_name = self.name + '.avi'
        if os.path.exists(file_name) and not settings.allow_override:
            logger.critical('Cannot overwrite existing video file: ' + file_name)
            raise Exception('Cannot overwrite existing video file: ' + file_name)
        else:            
            video_writer= cv2.VideoWriter(self.name + '.avi', fourcc, self.fps, (width, height))

        if not web_cam.isOpened():
            logger.warning('Recorder.run: Could not open webcam: ')
            raise Exception('Recorder.run: Could not open webcam')
    
        while web_cam.isOpened():
            # Capture frame-by-frame
            is_reading, frame = web_cam.read()
    
            if is_reading and recording:
                if self.mirror:
                    # Mirror the video if needed
                    frame = cv2.flip(frame, 1)

                # Saves for video
                video_writer.write(frame)
    
                # Display the resulting frame
                cv2.imshow(self.name, frame)
            else:
                break
    
            if cv2.waitKey(1) & 0xFF == ord(' '): #quit on space
                on_button_record()
                break
    
        # When everything done, release the capture
        web_cam.release()
        video_writer.release()
        cv2.destroyWindow(self.name)

class Video_Displayer(threading.Thread):
    file_name = ''
    mirror = False

    def __init__(self, file_name, mirror = False):
        threading.Thread.__init__(self)
        self.file_name = file_name
        self.mirror = mirror

    def run(self):
        video_input = cv2.VideoCapture(self.file_name)
        fps = int(video_input.get(cv2.CAP_PROP_FPS))
        logger.info('Video ' + self.file_name + ' running at fps=' + str(int(fps)))

        if not video_input.isOpened():
            logger.warning('display_video: Could not open video file for reading: ')
            raise Exception('display_video: Could not open video file for reading')
        while video_input.isOpened():
            #Get the next frame
            is_reading, frame = video_input.read()

            if is_reading:
                if self.mirror:
                    frame = cv2.flip(frame, 1)

                #Display the resulting frame
                cv2.imshow(self.file_name, frame)

            #Have the key to exit be somehting noone will press
            if cv2.waitKey(fps) & 0xFF == ord('¬'):
                break
        
        video_input.release()
        cv2.destroyWindow(self.file_name)

class Image_Displayer(threading.Thread):
    file_name = ''
    mirror = False
    time = 0

    def __init__(self, file_name, time, mirror = False):
        threading.Thread.__init__(self)
        self.file_name = file_name
        self.mirror = mirror
        self.time = time

    def run(self):
        image = cv2.imread(self.file_name)
        cv2.imshow(self.file_name, image)
        if cv2.waitKey(self.time) & 0xFF == ord('¬'):
            cv2.destroyAllWindows() # destroys the window showing image


class Subject():
    name = 'un-named'
    stimuli = []
    current_stimulus = -1

    def __init__(self, name, stimuli):
        self.name = name
        self.stimuli = stimuli

    def next_stimulus(self):
        self.current_stimulus += 1
        if self.current_stimulus < len(self.stimuli):
            stimulus = self.stimuli[self.current_stimulus].strip()
            return stimulus, self.determine_stimulus_type(stimulus)
        else:
            return None, None

    def current_stimulus_value(self):
        if self.current_stimulus < len(self.stimuli):
            stimulus_type = self.determine_stimulus_type(self.current_stimulus)
            stimulus = format_stimulus_output(self.stimuli[self.current_stimulus].strip(), stimulus_type)
            return stimulus, stimulus_type
        else:
            return 'None', None

    def determine_stimulus_type(self, stimulus):
        is_file = os.path.isfile(stimulus)
        if is_file:
            img_type = imghdr.what(stimulus)
            if img_type != None:
                return 'i'
            else:
                return 'v'
        return 't'

    def format_stimulus_output(self, stimulus, stimulus_type):
        if stimulus_type == 'i' or stimulus_type == 'v':
            return os.path.abspath(stimulus)
        return stimulus

main()