import cv2
import tkinter as tk
from tkinter import filedialog
import threading
import traceback
import sys
import logging
import os
import time
from PIL import Image, ImageTk

'''
Program data global variables
'''
#backend
logger = None
settings = None

#experiment data
webcam_num = 1
study_name = ''
study_files = []
stimulus_type = ''
stimuli_set = []
current_stimulus = 0
subject_id_entry_box = None
subject_id = 'No_Subject_ID'

#recording
window = None
recorder = None
recording = False
just_started = True
keep_displaying = True
can_start_recording = True

#files
out_dir = '.'
video_path = None
video_id = ''
last_video_id = None

#tk ui
main_frame = None
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

'''
Core program methods
'''
def main():
    '''
    First method called in this thread of program execution.
    Runs through a servies of initialization steps and then loads the gui.
    Once the gui is loaded, the gui takes over control of program execution from there onwards.
    '''

    load_config()
    init_vars()
    init_logging()
    init_gui()

def load_config():
    '''
    Loads the user settings from the config.csv file. If the file is not pressent or is corrputed, it will use default values
    and write a new config file, overwritting the old one if it is present.
    '''

    global ui_element_color, backcolor, forecolor, allow_override
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
        write_config_file()

def write_config_file():
    '''
    This method should only be called if the config file is corrupted or missing. It re-writes the config data and replaces all
    data with the default values, or the last loaded non-corrupt data value if such a data value is present.

    If this operations fails, the program will continue to run, but no config file will be generated.
    '''

    try:
        with open('config.csv', 'w') as config:
            print('allow_override,' + str(allow_override), file=config)
            print('backcolor,' + backcolor, file=config)
            print('forecolor,' + forecolor, file=config)
            print('ui_element_color,' + ui_element_color, file=config)
    except Exception as err:
        message = 'Attempt to recover config file failed: Could not write new config file' 
        logger.critical(message + ': ' + str(err))
        pop_up(message)

def init_vars():
    '''
    Initializes object variables from imports
    '''

    global display_timer, recording_timer
    display_timer = Timer()
    recording_timer = Timer()

def init_logging():
    '''
    Initializes the loggins system. The logging system is intended to allow the program to save data about each run to disk,
    and the logger itself will re-write any existing logs each time so as to conserve space and avoid cluttering the running
    directory with files. This method also triggers the first log write.

    Most methods in this program trigger a log call. For simplicity, the calls to logging are not mentioned in the method
    descriptions in general.
    '''

    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('SignRecorder.log', mode='w')
    logger.addHandler(file_handler)
    file_handler_format = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
    file_handler.setFormatter(file_handler_format)
    logger.info('Starting log')

def find_webcams(search_num):
    '''
    Searches to see how many webcams are attactched to the current system. This is done by attempting to open each webcam from
    number 0 (the default webcam) to number search_num, which is given to the method. If the webcam opens, then the program knows
    it has found a wewbcam; if not, the webcam either cannot be accessed by the program or is not present. All opened webcams are
    closed after searching, and not webcam inpout is recorded at this step.

    Parameters:
        search_num: The number of webcams for which to search
    '''

    global webcam_num
    webcam_num = 0
    for i in range(search_num):
        webcam_i = cv2.VideoCapture(i)
        if webcam_i.isOpened():
            webcam_num += 1
            webcam_i.release()
        logger.info(str(webcam_num) + ' webcams found for recording')

def init_gui():
    '''
    Initializes the gui. The gui is created in a maximized state and takes over main-thread program execution. Note that all gui
    operations should remain on the main thread, except where the gui allows (suchs as in triggered events). This method also sets
    up the key_tracker to manage keypress events and attempt to authenticate them (since some OS's will trigger a key press and / 
    or release repeatedly when a key is help down).

    The gui also maps the default close event (~the red X) to an ooperations that cleans up the program state properly. This
    should help to prevent memory leaks on an unexpected closure.
    '''

    global width, height, window, key_tracker, main_frame

    #Master window
    window = tk.Tk()
    window.wm_title('Sign Recorder')
    window.config(background = backcolor)
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()
    window.geometry("%dx%d+0+0" % (width, height))

    #Main Frame in window
    main_frame = MainFrame(window, background = backcolor)
    main_frame.prepare_display()
    main_frame.pack(side="top", fill="both", expand=True)

    #input
    key_tracker = KeyTracker()
    window.bind_all('<KeyPress>', key_tracker.report_key_press)
    window.bind_all('<KeyRelease>', key_tracker.report_key_release)
    key_tracker.track('space')

    #Exitting
    window.protocol("WM_DELETE_WINDOW",  on_close)
    
    #Show window
    window.mainloop()

def on_key_press(event):
    '''
    Called whenever a key press event is detected. This method should not be linked to key press events directly; the use of the
    KeyTracker class is necessary to authenticate key presses as valid before attempting to respond to them.

    If this program has just started, the program runs a different method to respond to the key press event to manage the yet
    un-initialized variables.
    '''

    global just_started
    if event.keysym == 'space':
        if just_started:
            on_button_space_press_just_started()
            just_started = False
        else:
            on_button_space_press()

def on_key_release(event):
    '''
    Called whenever a key release event is detected. This method should not be linked to key release events directly; the use 
    of the KeyTracker class is necessary to authenticate key releases as valid before attempting to respond to them.
    '''
    if event.keysym == 'space':
        on_button_space_release()

def on_button_space_press_just_started():
    '''
    This method should be called the first time each subject first does an authenticated space press. It creates their session and 
    transfers to the stimulus viewing screen. THe stimulus will be displayed there but recording will not begin tunil the next 
    authenticated space press is detected.
    '''

    global video_id, subject_id, last_video_id
    last_video_id = video_id
    video_id = os.path.basename(stimuli_set[current_stimulus].strip())
    subject_id = subject_id_entry_box.get().strip()
    logger.info('Starting session for ' + subject_id + ' for the first time ' + str(just_started))
    load_stimulus_just_started()

def on_button_space_press():
    '''
    This method should be called every time space is pressed (if that press has been authenticated), except the first. It proceeds
    to the next stimulus and will begin recording, ending the current stimulus and recording. It also ends the recording_timer if 
    it was running, and updates program state tracking variables to refect the current state of the progam.

    If there are mno more stimuli to run, the program displays a pop-up message stating that data collection is complete.
    '''

    global recording, video_id, last_video_id
    logger.info('on_button_space_press: current_stimulus=' + str(current_stimulus) + ' recording=' + str(recording))
    if recording:
        recording = False
        if recording_timer.active():
            recording_timer.end()
        if current_stimulus >= len(stimuli_set):
            main_frame.select_start_experiment()
            pop_up('All data for ' + subject_id + ' has been collected')
            reset_for_next_subject()
        else:
            last_video_id = video_id
            video_id = os.path.basename(stimuli_set[current_stimulus].strip())
            load_stimulus()

def on_button_space_release():
    '''
    This method should be called when space is released (if that release has been authenticated). It begins recording and starts
    the recording timer. It also updates program state tracking variables to refect the current state of the progam.
    '''

    global recording, current_stimulus, keep_displaying, recorder
    if can_start_recording and current_stimulus < len(stimuli_set):
        logger.info('on_button_space_release: current_stimulus=' + str(current_stimulus) + '; recording starting')
        recording = True
        keep_displaying = False
        current_stimulus += 1
        recording_timer.begin()
        recorder = Recorder(subject_id + '-' + video_id, True)
        recorder.begin()
    else:
        logger.warning('on_button_space_release: can_start_recording is False, video must end before the signer may be recorded')

def load_stimulus_just_started():
    '''
    Loads and displays the first stimulis for the current subject. It also starts the display timer, which measures the time that
    a stimulus is displayed before signing.
    '''

    global keep_displaying
    logger.info('load_stimulus_just_started: current_stimulus=' + str(current_stimulus) + ' stimulus type=' + str(stimulus_type))

    keep_displaying = True
    stimulus = stimuli_set[current_stimulus].strip()

    if stimulus_type == 'Image':
        display_timer.begin()
        Image_Displayer(stimulus).begin()
    elif stimulus_type == 'Video':
        display_timer.begin()
        Video_Displayer(stimulus).begin()

def load_stimulus():
    '''
    Loads and displays the next stimulis for the current subject, but should not be used for the first stimulus of a subjecct.
    It resets the display timer, which measures the time that a stimulus is displayed before signing.

    Later, it will also write timer output to a meta file with the same name as the output file. Timer data it not yet verified
    though, so it is not ready for use.
    '''

    global keep_displaying
    logger.info('load_stimulus: current_stimulus=' + str(current_stimulus) + ' stimulus type=' + str(stimulus_type))

    keep_displaying = True
    stimulus = stimuli_set[current_stimulus].strip()
    if display_timer.active():
        display_timer.end()
        #write_meta(out_dir, subject_id + '-' + last_video_id)

    if stimulus_type == 'Image':
        display_timer.begin()
        Image_Displayer(stimulus).begin()
    elif stimulus_type == 'Video':
        display_timer.begin()
        Video_Displayer(stimulus).begin()

def reset_for_next_subject():
    '''
    
    '''

    global subject_id, just_started, current_stimulus, keep_displaying, can_start_recording
    logger.info('Resetting the environment for the next subject')

    key_tracker.last_press_time = 0
    key_tracker.last_release_time = 0
    key_tracker.last_release_callback_time = 0
    key_tracker.first_callback_call = True
    key_tracker.last_event_was_press = False

    current_stimulus = 0
    keep_displaying = True
    can_start_recording = True
    subject_id = 'No_Subject_ID'
    just_started = True
    subject_id_entry_box.delete(0, last='end')

def pop_up(message):
    '''
    Creates a pop-up window to display a message. Please only call this method for important errors such as files that fail
    to load--each pop up will take focue from the main window and thus disrupt the user.
    '''

    global pop_up_window
    padding_x = 10
    padding_y = 10

    pop_up_window = tk.Tk()
    pop_up_window.wm_title('Message')
    pop_up_window.config(background=backcolor)

    pop_up_text = tk.Text(pop_up_window, font = default_font, height = 5, width = 70, background = ui_element_color, foreground = forecolor)
    pop_up_text.insert(tk.INSERT, message)
    pop_up_text.config(state = 'disabled')
    pop_up_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)

    select_files_button = tk.Button(pop_up_window, text ="Close", command = pop_up_window.destroy, font = default_font, height = 3, width = 10, background = ui_element_color, foreground = forecolor)
    select_files_button.grid(row=1, column=0)

    pop_up_window.mainloop()

def write_meta(path, name):
    '''
    Writes out a meta-file that contains metadata about the recorded video. The data is:
        stimulus_name: the name of the file used as a stimulus for this recording
        display_time: the amount of time the stimulus was displayed before recording
        recording_time: the time length of the recording
        total_time: the total time for this step of the experiment, = display_time + recording_time
    '''

    logger.info('writing meta file at path=' + path + ' with name=' + name)
    file_name = os.path.join(path, name + '.meta.csv')
    try:
        if os.path.exists(file_name) and not allow_override:
            message = 'Cannot overwrite existing meta file: '
            logger.critical(message + file_name)
            pop_up(message + '\n' + file_name)
            raise Exception(message + file_name)
        with open(file_name, 'w') as meta:
            print('stimulus_name,' + file_name)
            print('display_time,' + str(display_timer.timespan), file=meta)
            print('recording_time,' + str(recording_timer.timespan), file=meta)
            print('total_time,' + str(display_timer.timespan + recording_timer.timespan), file=meta)
    except Exception as err:
        message = 'Failed to write meta file: ' + file_name
        logger.critical(message + ': ' + str(err))
        pop_up(message)
        raise Exception(message)

def on_close():
    '''
    Handles properly closing the program and its spawned resources. As much as possible, all close events should be routed to
    this method rather than immediately calling an exit function.
    '''

    logger.info('Program closing due to user command')
    window.destroy()
    try:
        recorder.end()
    except:
        pass
    sys.exit(0)

def get_proper_resize_dimensions_for_fullscreen(img):
    '''
    This method gets the largest-area resize of an image to be displayed on a fullscreen display without allowing any of the
    image to overflow off-screen. It maintains the image aspect ratio.
    '''

    #Get image dimensions
    original_width = img.width
    original_height = img.height

    #Get the scalars that transform the original size into the fullscreen dize
    width_scalar = width / original_width
    height_scalar = height / original_height

    #Our goal is to make the image as largs as possible without goinf over the screen size.
    #We also do not want to loose out aspect ratio. So let's see whether using the width_scalar
    #   or the height_scalar does that best
    width_based_scaling_height = original_height * width_scalar
    width_based_scaling_valid = True
    if width_based_scaling_height > height:
        width_based_scaling_valid = False

    height_based_scaling_width = original_width * height_scalar
    height_based_scaling_valid = True
    if height_based_scaling_width > width:
        height_based_scaling_valid = False

    if width_based_scaling_valid and not height_based_scaling_valid:
        return width, width_based_scaling_height
    else:
        return height_based_scaling_width, height

'''
Data and user-input classes
'''
class Recorder():
    '''
    This class handles all recording using the webcam, and writes recrodings to disk.
    '''

    name = ''
    mirror = False
    web_cam = None
    video_writer = None

    def __init__(self, name, mirror):
        '''
        Initializes the Recorder. Parameters:
            name: The name to five to the recording file
            mirror: Whether the recording should be mirrored when saved to disk
        '''

        logger.info('Recorder.__init__: name=' + self.name + ' mirror=' + str(mirror))
        self.name = name
        self.mirror = mirror

    def begin(self):
        '''
        Begins recording from the webcam. The recording will continue untill end is called, or until 1 is pressed.
        Note that pressing 1 to quit should be used for debug purposes only
        '''

        # Capturing video from webcam:
        self.web_cam = cv2.VideoCapture(0)
        fps = self.web_cam.get(cv2.CAP_PROP_FPS)

        #get width and height of reading frame
        width = int(self.web_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.web_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
        # Define the codec and 
        fourcc = cv2.VideoWriter_fourcc(*"XVID")

        #create VideoWriter object
        file_name = os.path.join(out_dir, self.name + '.avi')
        if os.path.exists(file_name) and not allow_override:
            message = 'Cannot overwrite existing video file: ' 
            logger.critical(message + file_name)
            pop_up(message + '\n' + file_name)
            raise Exception(message + file_name)
        else:
            self.video_writer = cv2.VideoWriter(file_name, fourcc, fps, (width, height))

        if not self.web_cam.isOpened():
            message = 'Could not open webcam'
            logger.warning(message)
            pop_up(message)
            raise Exception(message)
    
        logger.info('Recorder.begin: starting recording loop')
        while self.web_cam.isOpened():
            # Capture frame-by-frame
            is_reading, frame = self.web_cam.read()
    
            if is_reading and recording:
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self.video_writer.write(frame)
            else:
                break
    
            if cv2.waitKey(1) & 0xFF == ord('1'): #quit on 1
                on_button_space_release()
                break
    
        self.end()
    
    def end(self):
        '''
        Ends the recording and releases resources.
        '''

        logger.info('Recorder.begin: recording ended, releasing resources')
        self.web_cam.release()
        self.video_writer.release()

class Video_Displayer():
    file_name = ''
    video_input = None
    fps = None
    display = None

    def __init__(self, file_name):
        logger.info('Video_Displayer.__init__: file_name=' + file_name)
        self.file_name = file_name

    def begin(self):
        global can_start_recording
        can_start_recording = False
        self.video_input = cv2.VideoCapture(self.file_name)
        self.fps = int(self.video_input.get(cv2.CAP_PROP_FPS))
        self.display = main_frame.page_show_stimuli.display_region
        logger.info('Video_Displayer.begin ' + self.file_name + ' running at fps=' + str(int(self.fps)))

        if not self.video_input.isOpened():
            message = 'Could not open video file for reading'
            logger.warning(message)
            pop_up(message)
            raise Exception(message)

        main_frame.select_show_stimuli()
        self.run_frame()        

    def run_frame(self):
        global can_start_recording
        #Get the next frame
        is_reading, frame = self.video_input.read()

        if is_reading:
            #Load the image for the current frame and convert to imagetk
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            img_width, img_height = get_proper_resize_dimensions_for_fullscreen(img)
            img = img.resize((int(img_width), int(img_height)))
            imgtk = ImageTk.PhotoImage(image=img)
            self.display.imgtk = imgtk
            self.display.configure(image=imgtk)
            if self.video_input.isOpened():
                self.display.after(self.fps, self.run_frame)
            else:
                self.end('Video_Displayer.run_frame: display ended due to unexpected closure of video_input')
                can_start_recording = True
        else:
            self.end('Video_Displayer.run_frame: display ended naturally')
            can_start_recording = True
            

    def end(self, message = 'Video_Displayer.run_frame ended'):
        logger.info(message)
        self.video_input.release()

class Image_Displayer():
    file_name = ''
    display = None

    def __init__(self, file_name):
        logger.info('Image_Displayer.__init__ ' + file_name)
        self.file_name = file_name

    def begin(self):
        self.display = main_frame.page_show_stimuli.display_region
        main_frame.select_show_stimuli()

        #Load the image for the current frame and convert to imagetk
        cv2image = cv2.imread(self.file_name)
        b,g,r = cv2.split(cv2image)
        cv2image = cv2.merge((r,g,b))
        img = Image.fromarray(cv2image)
        img_width, img_height = get_proper_resize_dimensions_for_fullscreen(img)
        img = img.resize((int(img_width), int(img_height)))
        imgtk = ImageTk.PhotoImage(image=img) 

        # Put it in the display window
        self.display.imgtk = imgtk
        self.display.configure(image=imgtk)

class KeyTracker():
    key = ''
    last_press_time = 0
    last_release_time = 0
    last_release_callback_time = 0
    first_callback_call = True
    last_event_was_press = False

    def track(self, key):
        logger.info('KeyTracker.track: key=' + key)
        self.key = key

    def is_pressed(self):
        press_time_test = time.time() - self.last_press_time < .1 #In seconds
        return press_time_test

    def report_key_press(self, event):
        if not self.last_event_was_press and event.keysym == self.key:
            self.last_event_was_press = True
            if not self.is_pressed():
                logger.info('KeyTracker.report_key_press: valid keypress detected: key=' + self.key)
                self.last_press_time = time.time()
                on_key_press(event)
            else:
                self.last_press_time = time.time()

    def report_key_release(self, event):
        if self.last_event_was_press and event.keysym == self.key:
            self.last_event_was_press = False
            self.last_release_time = time.time()
            timer = threading.Timer(.5, self.report_key_release_callback, args=[event]) #In seconds
            timer.start()
    
    def report_key_release_callback(self, event):
        if self.first_callback_call:
            self.last_release_callback_time = time.time()
            self.first_callback_call = False
        if time.time() - self.last_release_callback_time > .5:
            self.last_release_callback_time = time.time()
            logger.info('KeyTracker.report_key_release_callback: key=' + self.key + ', is released= ' + str((not self.is_pressed())))
            if not self.is_pressed():
                on_key_release(event)
            
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


'''
UI classes and layout management
'''

def arrange_header_in(page):
    button_frame = page.button_frame
    top_bar_buttons = []
    #Place buttons in the top-level button frame
    top_bar_buttons.append(tk.Button(button_frame, text="Main Menu", font=default_font, command=main_frame.select_main_menu, background = ui_element_color, foreground = forecolor))
    top_bar_buttons.append(tk.Button(button_frame, text="Create Experiment", font=default_font, command=main_frame.select_create_experiment, background = ui_element_color, foreground = forecolor))
    top_bar_buttons.append(tk.Button(button_frame, text="Start Experiment", font=default_font, command=main_frame.select_start_experiment, background = ui_element_color, foreground = forecolor))
    
    #Grid buttons
    col = 0
    for button in top_bar_buttons:
        button.grid(row=0, column=col, pady=10)
        col += 1

    button_frame.grid(row=0, column=0)

class Page(tk.Frame):
    button_frame = None

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.config(background = backcolor)
        self.button_frame = tk.Frame(self, background = backcolor)

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
        Version: 0.2.1beta
        Developer: Jeffrey Sardina 

        SignRecorder is a simple program for recording and saving 
        video files for sign language data collection and
        experiments. It is currently hosted on GitHub
        (https://github.com/Jeffrey-Sardina/SignRecorder)
        as an open-source project.
 
        To get started, click on either 'Create Experiemnt' or 
        'Start Experiment'. The program will guide you through
        loading stimuli and experimental methods. Once you have
        made an experiemnt, save it so that you can load it later.
        '''

        arrange_header_in(self)

        file_text = tk.Text(self, font = default_font, height = 15, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, about_text)
        file_text.config(state = 'disabled')
        file_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

class Page_Create_Experiment(Page):
    files = []
    option_selected = None
    entry = None
    selected_files_info_text = None

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()
        
    def init_elements(self):
        arrange_header_in(self)

        padding_x = 10
        padding_y = 10

        stimulus_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        stimulus_text.insert(tk.INSERT, '\nSelect Stimulus Type')
        stimulus_text.tag_configure("center", justify='center')
        stimulus_text.tag_add("center", 1.0, "end")
        stimulus_text.config(state = 'disabled')
        stimulus_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        options = ['Video', 'Image']
        default_option = options[0]
        self.option_selected = tk.StringVar(self)
        option_menu = tk.OptionMenu(self, self.option_selected, *options)
        self.option_selected.set(default_option)
        option_menu.config(background = ui_element_color, foreground = forecolor, height = 3, width = 30, font = default_font)
        option_menu.grid(row=2, column=0, padx=padding_x, pady=padding_y)

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
        select_text.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Select files", command = self.load_files, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)

        file_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, '\nOnce you are done, press create experiment to save an experiment file')
        file_text.tag_configure("center", justify='center')
        file_text.tag_add("center", 1.0, "end")
        file_text.config(state = 'disabled')
        file_text.grid(row=5, column=0, padx=padding_x, pady=padding_y)

        select_files_button = tk.Button(self, text ="Create Experiment", command = self.create_experiment, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_files_button.grid(row=6, column=0, padx=padding_x, pady=padding_y)

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
        global subject_id_entry_box

        arrange_header_in(self)

        padding_x = 10
        padding_y = 10

        file_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        file_text.insert(tk.INSERT, '\nSelect an experiment file to load')
        file_text.tag_configure("center", justify='center')
        file_text.tag_add("center", 1.0, "end")
        file_text.config(state = 'disabled')
        file_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose file", command = self.load_experiment, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_file_button.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        dir_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        dir_text.insert(tk.INSERT, '\nSelect a folder in which to save the output')
        dir_text.tag_configure("center", justify='center')
        dir_text.tag_add("center", 1.0, "end")
        dir_text.config(state = 'disabled')
        dir_text.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose output folder", command = self.load_dir, font = default_font, height = 3, width = 30, background = ui_element_color, foreground = forecolor)
        select_file_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)

        entry_text = tk.Text(self, font = default_font, height = 3, width = 70, background = ui_element_color, foreground = forecolor)
        entry_text.insert(tk.INSERT, '\nEnter subject ID')
        entry_text.tag_configure("center", justify='center')
        entry_text.tag_add("center", 1.0, "end")
        entry_text.config(state = 'disabled')
        entry_text.grid(row=5, column=0, padx=padding_x, pady=padding_y)

        subject_id_entry_box = tk.Entry(self, font = default_font, background = ui_element_color, foreground = forecolor)
        subject_id_entry_box.grid(row=6, column=0, padx=padding_x, pady=padding_y)

        how_to_string = '''
        When you are ready to begin the experiment, press the space bar. 

        Once you are ready to sign based on what you see, press the space
        bar to start recording.

        Once you are done signing, press the space bar again. You will then
        see the next prompt and the program will begin recording.
        '''
        how_to_text = tk.Text(self, font = default_font, height = 9, width = 70, background = ui_element_color, foreground = forecolor)
        how_to_text.insert(tk.INSERT, how_to_string)
        how_to_text.config(state = 'disabled')
        how_to_text.grid(row=7, column=0, padx=padding_x, pady=padding_y)

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
            stimuli_set = study_files
        except Exception as err:
            message = 'Could not load experiment file'
            logger.error(message + ': ' + str(err))
            pop_up(message)

class Page_Show_Stimuli(Page):
    display_region = None

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_display_region()

    def init_display_region(self):
        self.display_region = tk.Label(self)
        self.display_region.config(background = "#000000")
        self.display_region.grid(row=0, column=0)
        
class MainFrame(tk.Frame):
    page_main_menu =  None
    page_create_experiment = None
    page_start_experiment = None
    page_show_stimuli = None

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.buttonframe = tk.Frame(main_frame, background = backcolor)
        self.config(background = backcolor)

    def prepare_display(self):
        #Pages
        self.page_main_menu = Page_Main_Menu(self, width = width, height = height, background = backcolor)
        self.page_create_experiment = Page_Create_Experiment(self, width = width, height = height, background = backcolor)
        self.page_start_experiment = Page_Start_Experiment(self, width = width, height = height, background = backcolor)
        self.page_show_stimuli = Page_Show_Stimuli(self, width = width, height = height, background = backcolor)

        #Container
        container = tk.Frame(self, background = backcolor)
        container.pack(side="top", fill="both", expand=True)

        #Place pages in the container frame
        self.page_main_menu.place(in_=container)
        self.page_create_experiment.place(in_=container)
        self.page_start_experiment.place(in_=container)
        self.page_show_stimuli.place(in_=container)

        #Show the main menu
        self.page_main_menu.show()

    def select_main_menu(self):
        self.set_fullscreen_exclusive(False)
        self.page_main_menu.lift()
        self.page_create_experiment.lower()
        self.page_start_experiment.lower()
        self.page_show_stimuli.lower()

    def select_create_experiment(self):
        self.set_fullscreen_exclusive(False)
        self.page_create_experiment.lift()
        self.page_main_menu.lower()
        self.page_start_experiment.lower()
        self.page_show_stimuli.lower()

    def select_start_experiment(self):
        self.set_fullscreen_exclusive(False)
        self.page_start_experiment.lift()
        self.page_create_experiment.lower()
        self.page_main_menu.lower()
        self.page_show_stimuli.lower()

    def select_show_stimuli(self):
        self.set_fullscreen_exclusive(True)
        self.page_show_stimuli.lift()
        self.page_main_menu.lower()
        self.page_create_experiment.lower()
        self.page_start_experiment.lower()

    def set_fullscreen_exclusive(self, fullscreen_exclusive):
        window.attributes('-fullscreen', fullscreen_exclusive)

'''
This code starts program execition. The entire program is run in a try-except statement so that, should any error occur:
    The program can write out the error to the command line
    The program can still run on on_close() function to try to clean up all resources
'''

try:
    main()
except Exception as e:
    trace = traceback.format_exc()
    print('Something bad happened ' + str(e) + '\n' + str(trace))
    on_close()