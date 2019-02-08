import cv2
import tkinter as tk
from tkinter import filedialog
import threading
import sys
import logging
import os
import time

#backend
logger = None
settings = None

#experiment data
webcam_num = 0
study_name = ''
study_files = []
stimulus_type = ''
stimuli_set = []
current_stimulus = 0

#recording
window = None
recording = False
just_started = True

#files
out_dir = '.'
video_path = None
video_id = None

#tk ui
pop_up_window = None
width = 0
height = 0
key_tracker = None

#timing
display_timer = None
recording_timer = None

#Settings
backcolor = '#000000'
ui_element_color = '#888888'
forecolor = '#000000'
allow_override = False

#text
default_font = 20

def main():
    init_vars()
    init_logging()
    #find_webcams(10)
    load_config()
    init_gui()

def init_vars():
    global display_timer, recording_timer
    display_timer = Timer()
    recording_timer = Timer()

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
        message = 'No cameras found for recording!'
        logger.critical(message)
        pop_up(message)
        raise Exception(message)

def load_config():
    Settings().load_config()

def init_gui():
    global width, height, window, key_tracker

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
    key_tracker = KeyTracker()
    window.bind_all('<KeyPress>', key_tracker.report_key_press)
    window.bind_all('<KeyRelease>', key_tracker.report_key_release)
    key_tracker.track('space')
    
    #Show window
    window.mainloop()

def on_key_press(event):
    global just_started
    if event.keysym == 'space':
        if just_started:
            on_button_space_press_just_started()
            just_started = False
        else:
            on_button_space_press()

def on_key_release(event):
    if event.keysym == 'space':
        on_button_space_release()
    elif event.keysym == 'Escape':
        on_button_exit()

def on_button_space_press_just_started():
    global video_id
    video_id = os.path.basename(stimuli_set[current_stimulus].strip())
    load_stimulus()

def on_button_space_press():
    global recording, video_id
    logger.info('on_button_space_press: current_stimulus=' + str(current_stimulus) + ' recording=' + str(recording))
    if recording:
        recording = False
        if recording_timer.active():
            recording_timer.end()
        video_id = os.path.basename(stimuli_set[current_stimulus].strip())
        load_stimulus()

def on_button_space_release():
    global recording, current_stimulus
    logger.info('on_button_space_release: current_stimulus=' + str(current_stimulus))
    recording = True
    current_stimulus += 1
    recording_timer.begin()
    Recorder(video_id, 30, True).begin()

def load_stimulus():
    logger.info('load_stimulus: current_stimulus=' + str(current_stimulus) + ' stimulus type=' + str(stimulus_type))
    stimulus = stimuli_set[current_stimulus].strip()
    if display_timer.active():
        display_timer.end()
        write_meta(out_dir, video_id)

    if stimulus_type == 'Text':
        display_timer.begin()
        pop_up_window = tk.Tk()
        text_label = tk.Label(pop_up_window, text = stimulus, font = default_font, justify='left', height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        text_label.grid(row=0, column=0)
    elif stimulus_type == 'Image':
        display_timer.begin()
        Image_Displayer(stimulus).begin()
    elif stimulus_type == 'Video':
        display_timer.begin()
        Video_Displayer(stimulus).begin()

def on_button_exit():
    global recording
    logger.log('on_button_exit--exitting program')
    if recording:
        recording = False
    sys.exit()

def pop_up(message):
    global pop_up_window
    padding_x = 10
    padding_y = 10

    pop_up_window = tk.Tk()
    pop_up_window.wm_title('Error Loading File')
    pop_up_window.config(background=backcolor)

    pop_up_text = tk.Text(pop_up_window, font = default_font, height = 5, width = 70, background = ui_element_color, foreground = forecolor)
    pop_up_text.insert(tk.INSERT, message)
    pop_up_text.config(state = 'disabled')
    pop_up_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)

    select_files_button = tk.Button(pop_up_window, text ="Close", command = pop_up_window.destroy, font = default_font, height = 3, width = 10, background = ui_element_color, foreground = forecolor)
    select_files_button.grid(row=1, column=0)

    pop_up_window.mainloop()

def write_meta(path, name):
    logger.info('writing meta file at path=' + path + ' with name=' + name)
    file_name = os.path.join(path, name + '.meta.csv')
    try:
        if os.path.exists(file_name) and not settings.allow_override:
            message = 'Cannot overwrite existing meta file:\n' + file_name
            logger.critical(message)
            pop_up(message)
            raise Exception(message)
        with open(file_name, 'w') as meta:
            print('display_time,' + str(display_timer.timespan), file=meta)
            print('recording_time,' + str(recording_timer.timespan), file=meta)
            print('total_time' + str(display_timer.timespan + recording_timer.timespan), file=meta)
    except Exception as err:
        message = 'Failed to write meta file: ' + file_name
        logger.critical(message + ': ' + str(err))
        pop_up(message)
        raise Exception(message)

class Settings():
    global allow_override

    def load_config(self):
        global ui_element_color, backcolor, forecolor
        try:
            with open('config.csv', 'r') as config:
                for line in config:
                    key, value = line.split(',', 1)
                    if key == 'allow_override':
                        allow_override = int(value) == 1
                    elif key == 'backcolor':
                        backcolor = value.strip()
                    elif key == 'forecolor':
                        forecolor = value.strip()
                    elif key == 'ui_element_color':
                        ui_element_color = value.strip()
        except Exception as err:
            message = 'Could not read config file'
            logger.error(message + ': ' + str(err))
            pop_up(message)
            raise

class Recorder():
    name = ''
    fps = 0
    mirror = False

    def __init__(self, name, fps, mirror):
        logger.info('Recorder.__init__: name=' + self.name + ' fps=' + str(self.fps) + ' mirror=' + str(mirror))
        self.name = name
        self.fps = fps
        self.mirror = mirror

    def begin(self):
        # Capturing video from webcam:
        web_cam = cv2.VideoCapture(0)

        #get width and height of reading frame
        width = int(web_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(web_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
        # Define the codec and 
        fourcc = cv2.VideoWriter_fourcc(*"XVID")

        #create VideoWriter object
        file_name = os.path.join(out_dir, self.name + '.avi')
        if os.path.exists(file_name) and not settings.allow_override:
            message = 'Cannot overwrite existing video file:\n' + file_name
            logger.critical(message)
            pop_up(message)
            raise Exception(message)
        else:
            video_writer= cv2.VideoWriter(file_name, fourcc, self.fps, (width, height))

        if not web_cam.isOpened():
            message = 'Could not open webcam'
            logger.warning(message)
            pop_up(message)
            raise Exception(message)
    
        logger.info('Recorder.begin: starting recording loop')
        while web_cam.isOpened():
            # Capture frame-by-frame
            is_reading, frame = web_cam.read()
    
            if is_reading and recording:
                if self.mirror:
                    # Mirror the video if needed
                    frame = cv2.flip(frame, 1)

                # Saves for video
                video_writer.write(frame)
            else:
                break
    
            if cv2.waitKey(1) & 0xFF == ord('1'): #quit on 1
                on_button_space_release()
                break
    
        # When everything done, release the capture
        logger.info('Recorder.begin: recording ended, releasing resources')
        web_cam.release()
        video_writer.release()

class Video_Displayer():
    file_name = ''

    def __init__(self, file_name):
        logger.info('Video_Displayer.__init__: file_name=' + file_name)
        self.file_name = file_name

    def begin(self):
        video_input = cv2.VideoCapture(self.file_name)
        fps = int(video_input.get(cv2.CAP_PROP_FPS))
        logger.info('Video_Displayer.begin ' + self.file_name + ' running at fps=' + str(int(fps)))

        if not video_input.isOpened():
            message = 'Could not open video file for reading'
            logger.warning(message)
            pop_up(message)
            raise Exception(message)

        cv2.namedWindow(self.file_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.file_name ,cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        while video_input.isOpened():
            #Get the next frame
            is_reading, frame = video_input.read()

            if is_reading:
                cv2.imshow(self.file_name, frame)
            else:
                logger.info('Video_Displayer.begin: display ended naturally')
                break

            if cv2.waitKey(fps) & 0xFF == ord('1'):
                logger.info('Video_Displayer.begin: display ended by user command')
                break
        
        video_input.release()
        cv2.destroyWindow(self.file_name)

class Image_Displayer():
    file_name = ''
    time = 0

    def __init__(self, file_name):
        logger.info('Image_Displayer.__init__ ' + file_name)
        self.file_name = file_name

    def begin(self):
        image = cv2.imread(self.file_name)
        cv2.namedWindow(self.file_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.file_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        logger.info('Image_Displayer.begin: showing image')
        cv2.imshow(self.file_name, image)
        if cv2.waitKey(self.time):
            logger.info('Image_Displayer.begin: image done showing, cleaning resources')
            cv2.destroyWindow(self.file_name)

class KeyTracker():
    key = ''
    last_press_time = 0
    last_release_time = 0

    def track(self, key):
        logger.info('KeyTracker.track: key=' + key)
        self.key = key

    def is_pressed(self):
        return time.time() - self.last_press_time < .1

    def report_key_press(self, event):
        if event.keysym == self.key:
            if not self.is_pressed():
                on_key_press(event)
            self.last_press_time = time.time()

    def report_key_release(self, event):
        if event.keysym == self.key:
            timer = threading.Timer(.1, self.report_key_release_callback, args=[event])
            timer.start()
    
    def report_key_release_callback(self, event):
        logger.info('KeyTracker.report_key_release_callback: key=' + self.key + ' is released= ' + str((not self.is_pressed())))
        if not self.is_pressed():
            on_key_release(event)
        self.last_release_time = time.time()
            
class Timer():
    start_time = 0
    end_time = 0
    timespan = 0

    def begin(self):
        self.start_time = time.time()
    
    def end(self):
        self.end_time = time.time()
        self.timespan = self.end_time - self.start_time

    def active(self):
        return self.start_time > self.end_time

class Page(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
    def show(self):
        self.lift()

class Page_Main_Menu(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):
        padding_x = 10
        padding_y = 10

        about_text = '''
        Version: 0.1
        Developer: Jeffrey Sardina 

        SignRecorder is a simple program for recording and saving 
        video '.avi' files for sign language data collection and
        experiments. It is currently hosted on GitHub
        (https://github.com/Jeffrey-Sardina/SignRecorder)
        as an open-source project.
 
        To get started, click on either 'Create Experiemnt' or 
        'Start Experiment'. The program will guide you through
        loading stimuli and experimental methods. Once you have
        made an experiemnt, save it so that you can load it later.
        '''

        file_text = tk.Text(self, font = default_font, height = 15, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, about_text)
        file_text.config(state = 'disabled')
        file_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)

class Page_Create_Experiment(Page):
    files = []
    option_selected = None
    entry = None
    selected_files_info_text = None

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()
        
    def init_elements(self):
        padding_x = 10
        padding_y = 10

        stimulus_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        stimulus_text.insert(tk.INSERT, '\nSelect Stimulus Type')
        stimulus_text.tag_configure("center", justify='center')
        stimulus_text.tag_add("center", 1.0, "end")
        stimulus_text.config(state = 'disabled')
        stimulus_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)

        options = ['Video', 'Image', 'Text']
        default_option = options[0]
        self.option_selected = tk.StringVar(self)
        option_menu = tk.OptionMenu(self, self.option_selected, *options)
        self.option_selected.set(default_option)
        option_menu.config(background = ui_element_color, foreground = forecolor, height = 3, width = 30, font = default_font)
        option_menu.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        filestring = '''
        Please Select the files to use for stimuli. These will be used during the experiment.
        --For videos or images, select the video or image files from your computer.
        --For text stimuli, select files contianing each stimulus in one file.
        '''

        select_text = tk.Text(self, font = default_font, height = 5, width = 70, background = ui_element_color, foreground = forecolor)
        select_text.insert(tk.INSERT, filestring)
        select_text.tag_configure("center", justify='center')
        select_text.tag_add("center", 1.0, "end")
        select_text.config(state = 'disabled')
        select_text.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Select files", command = self.load_files, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        file_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, '\nOnce you are done, press create experiment to save an experiment file')
        file_text.tag_configure("center", justify='center')
        file_text.tag_add("center", 1.0, "end")
        file_text.config(state = 'disabled')
        file_text.grid(row=4, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Create Experiment", command = self.create_experiment, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=5, column=0, padx=padding_x, pady=padding_y)

        self.selected_files_info_text = tk.Text(self, font = default_font, height = 27, width = 70, background = ui_element_color, foreground = forecolor)
        self.selected_files_info_text.insert(tk.INSERT, 'Files selected:\n')
        self.selected_files_info_text.config(state = 'disabled')
        self.selected_files_info_text.grid(row=0, column=1, rowspan = 20, padx=padding_x, pady=padding_y)

    def load_files(self):
        logger.info('Page_Create_Experiment: load_files')
        self.files = filedialog.askopenfilenames(parent=self, initialdir="/", title='Select Files' + self.option_selected.get() + ' files')
        display_text = 'Files selected:\n'
        for file_name in self.files:
            display_text += os.path.basename(file_name) + '\n'
        self.selected_files_info_text.config(state = 'normal')
        self.selected_files_info_text.delete(1.0, tk.END)
        self.selected_files_info_text.insert(tk.INSERT, display_text)
        self.selected_files_info_text.config(state = 'disabled')

    def create_experiment(self):
        logger.info('Page_Create_Experiment: create_experiment')
        experimant_name = filedialog.asksaveasfilename(initialdir = "/", title = "Save file", filetypes = (("experiment files","*.exp"), ("all files","*.*")))
        try:
            with open(experimant_name, 'w') as experiment:
                print('type,' + self.option_selected.get(), file=experiment)
                for exp_file in self.files:
                    print('file,' + exp_file, file=experiment)
        except Exception as err:
            message = 'Error: Could not write experiment file'
            logger.error(message + ': ' + str(err))
            pop_up(message)

class Page_Start_Experiment(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):
        padding_x = 10
        padding_y = 10

        file_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, '\nSelect an experiment file to load')
        file_text.tag_configure("center", justify='center')
        file_text.tag_add("center", 1.0, "end")
        file_text.config(state = 'disabled')
        file_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose file", command = self.load_experiment, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_file_button.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        dir_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        dir_text.insert(tk.INSERT, '\nSelect a folder in which to save the output')
        dir_text.tag_configure("center", justify='center')
        dir_text.tag_add("center", 1.0, "end")
        dir_text.config(state = 'disabled')
        dir_text.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose output folder", command = self.load_dir, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_file_button.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        how_to_string = '''
        When you are ready to begin the experiment, press and hold the space bar. 
        You will then see the image prompt.

        Once you are ready to sign based on what you see, remove your hands from 
        the space bar and begin to sign.

        Once you are done signing, place your hands back on space and hold to advance.
        '''
        how_to_text = tk.Text(self, font = default_font, height = 9, width = 70, background = ui_element_color, foreground = forecolor)
        how_to_text.insert(tk.INSERT, how_to_string)
        how_to_text.config(state = 'disabled')
        how_to_text.grid(row=4, column=0, padx=padding_x, pady=padding_y)

    def load_dir(self):
        global out_dir
        logger.info('Page_Start_Experiment: load_dir')
        try:
            out_dir = filedialog.askdirectory(parent = self, initialdir="/", title='Select Save Folder')
        except Exception as err:
            message = 'Could not load the selected directory'
            logger.error(message + ': ' + str(err))
            pop_up(message)

    def load_experiment(self):
        global study_name, stimulus_type, stimuli_set
        logger.info('Page_Start_Experiment: load_experiment')
        experiment_file = filedialog.askopenfilename(parent=self, initialdir="/", title='Select Experiment')
        try:
            with open(experiment_file, 'r') as experiment:
                for line in experiment:
                    key, value = line.strip().split(',')
                    if key == 'name':
                        study_name = value.strip()
                    elif key == 'type':
                        stimulus_type = value.strip()
                    elif key == 'file':
                        study_files.append(value.strip())

            if stimulus_type == 'Text':
                text_stimuli = []
                with open(study_files[0]) as data:
                    for line in data:
                        text_stimuli.append(line)
                stimuli_set = text_stimuli
            else:
                stimuli_set = study_files
        except Exception as err:
            message = 'Could not load experiment file'
            logger.error(message + ': ' + str(err))
            pop_up(message)

class MainFrame(tk.Frame):
    page_main_menu =  None
    page_create_experiment = None
    page_start_experiment = None

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.config(background = backcolor)

        #Pages
        self.page_main_menu = Page_Main_Menu(self, width = width, height = height, background = backcolor)
        self.page_create_experiment = Page_Create_Experiment(self, width = width, height = height, background = backcolor)
        self.page_start_experiment = Page_Start_Experiment(self, width = width, height = height, background = backcolor)

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
        self.page_create_experiment.lower()
        self.page_start_experiment.lower()

    def select_create_experiment(self):
        self.page_create_experiment.lift()
        self.page_main_menu.lower()
        self.page_start_experiment.lower()

    def select_start_experiment(self):
        self.page_start_experiment.lift()
        self.page_create_experiment.lower()
        self.page_main_menu.lower()

main()