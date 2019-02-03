import cv2
import tkinter as tk
from tkinter import filedialog
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
data_label = None
pop_up_window = None

#exp data
subjects = []
records_since_last_next = 0
current_subject = 0

#Themeing
backcolor = '#000000'
ui_element_color = '#555555'
forecolor = '#ffffff'

#text
default_font = 20
controls_text = '''
Space: start / stop recording
Enter: next stimulus / subject
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

into_text = '''
To get started, click on either 'Create Experiemnt' or 
'Start Experiment'. The program will guide you through
loading stimuli and experimental methods. Once you have
made an experiemnt, save it so that you can load it later.
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
    #Master window
    window = tk.Tk()
    window.wm_title('Sign Recorder')
    window.config(background = backcolor)
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()
    window.geometry("%dx%d+0+0" % (width, height))

    #Main Frame in window
    main_frame = MainFrame(window, background = backcolor)
    main_frame.pack(side="top", fill="both", expand=True)

    #input
    window.bind_all('<KeyRelease>', on_key_release)
    
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

class Settings():
    cam_num = 0
    display_cam_feed = False
    allow_override = False

    def __init__(self):
        self.load_config()

    def load_config(self):
        global ui_element_color, backcolor, forecolor
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
                    if key == 'backcolor':
                        backcolor = value.strip()
                    if key == 'forecolor':
                        forecolor = value.strip()
                    if key == 'ui_element_color':
                        ui_element_color = value.strip()
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
            stimulus = self.format_stimulus_output(self.stimuli[self.current_stimulus].strip(), stimulus_type)
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

class Page(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
    def show(self):
        self.lift()

class Page_Main_Menu(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
        self.init_elements()

    def init_elements(self):
        label = tk.Label(self, text=about_text + '\n\n' + into_text, justify='left', font = default_font, background = backcolor, foreground = forecolor)
        label.pack(side="top")

class Page_Create_Experiment(Page):
    files = []
    option_selected = None
    entry = None

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
        self.init_elements()
        
    def init_elements(self):
        padding_x = 10
        padding_y = 10

        stimulus_label = tk.Label(self, text = 'Select Stimulus Type', font = default_font, justify='left', height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        stimulus_label.grid(row=0, column=0, padx=padding_x, pady=padding_y)

        options = ['Video', 'Image', 'Text']
        default_option = options[0]
        self.option_selected = tk.StringVar(self)
        option_menu = tk.OptionMenu(self, self.option_selected, *options)
        self.option_selected.set(default_option)
        option_menu.config(background = ui_element_color, foreground = forecolor)
        option_menu.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        name_label = tk.Label(self, text = 'Enter the name of the experiment', font = default_font, justify='left', height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        name_label.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        self.entry = tk.StringVar(self)
        name_entry = tk.Entry(self, textvariable = self.entry)
        name_entry.focus_set()
        name_entry.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        file_text = '''
        Please Select the files to use for stimuli. These will be used during the experiment.
        --For videos or images, select the video or image files from your computer.
        --For text stimuli, select a plaintext file contianing each stimulus on a separate line.
        '''
        file_label = tk.Label(self, text = file_text, font = default_font, justify='left', height = 5, width = 70, background = ui_element_color, foreground = forecolor)
        file_label.grid(row=4, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Select files", command = self.load_files, font = (None, 15), height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=5, column=0, padx=padding_x, pady=padding_y)

        file_label = tk.Label(self, text = 'Once you are done, press create experiment!', font = default_font, justify='left', height = 5, width = 70, background = ui_element_color, foreground = forecolor)
        file_label.grid(row=6, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Create Experiment", command = self.create_experiment, font = (None, 15), height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=7, column=0, padx=padding_x, pady=padding_y)

    def load_files(self):
        self.files = filedialog.askopenfilenames(parent=self, initialdir="/", title='Select ' + self.option_selected.get() + ' files')

    def create_experiment(self):
        experimant_name = self.entry.get() + '.exp'
        if os.path.exists(experimant_name) and not settings.allow_override:
            logger.critical('File already exists and cannot be overwritten due to config specifications')
        try:
            with open(experimant_name, 'w') as experiment:
                print('name,' + self.entry.get(), file=experiment)
                print('type,' + self.option_selected.get(), file=experiment)
                for exp_file in self.files:
                    print('file,' + exp_file, file=experiment)
        except:
            pass

class Page_Start_Experiment(Page):
    name = ''
    files = []
    type = ''

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
        self.init_elements()

    def init_elements(self):
        global record_button, data_label
        padding_x = 10
        padding_y = 10

        file_label = tk.Label(self, text = 'Select and experiment ile to load', font = default_font, justify='left', height = 5, width = 70, background = ui_element_color, foreground = forecolor)
        file_label.grid(row=0, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose file", command = self.load_experiment, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_file_button.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        file_label = tk.Label(self, text = 'Press Next to get started!', font = default_font, justify='left', height = 5, width = 70, background = ui_element_color, foreground = forecolor)
        file_label.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        record_button = tk.Button(self, text ="Record", command = on_button_record, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        record_button.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        next_button = tk.Button(self, text ="Next", command = on_button_next, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        next_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)

    def load_experiment(self):
        experiment_file = filedialog.askopenfilename(parent=self, initialdir="/", title='Select Experiment')
        try:
            with open(experiment_file, 'r') as experiment:
                for line in experiment:
                    key, value = line.strip().split(',')
                    if key == 'name':
                        self.name = value.strip()
                    if key == 'type':
                        self.type = value.strip()
                    if key == 'file':
                        self.files.append(value.strip())
        except:
            pass

class MainFrame(tk.Frame):
    page_main_menu =  None
    page_create_experiment = None
    page_start_experiment = None

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.config(background = backcolor)

        #Pages
        self.page_main_menu = Page_Main_Menu(self)
        self.page_create_experiment = Page_Create_Experiment(self)
        self.page_start_experiment = Page_Start_Experiment(self)

        #Page Navigation
        buttonframe = tk.Frame(self, background = backcolor)
        container = tk.Frame(self, background = backcolor)
        buttonframe.pack(side="top", fill="x", expand=False)
        container.pack(side="top", fill="both", expand=True)

        #Place pages in the container frame
        self.page_main_menu.place(in_=container)
        self.page_create_experiment.place(in_=container)
        self.page_start_experiment.place(in_=container)

        #Place buttons in the top-level button frame
        b1 = tk.Button(buttonframe, text="Main Menu", font=default_font, command=self.select_main_menu, background = ui_element_color, foreground = forecolor)
        b2 = tk.Button(buttonframe, text="Create Experiment", font=default_font, command=self.select_create_experiment, background = ui_element_color, foreground = forecolor)
        b3 = tk.Button(buttonframe, text="Start Experiment", font=default_font, command=self.select_start_experiment, background = ui_element_color, foreground = forecolor)

        #Pack buttons
        b1.pack(side="left")
        b2.pack(side="left")
        b3.pack(side="left")

        #Show the main menu
        self.page_main_menu.show()

    def select_main_menu(self):
        self.page_main_menu.lift()

    def select_create_experiment(self):
        self.page_create_experiment.lift()

    def select_start_experiment(self):
        self.page_start_experiment.lift()


main()