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
import abc
import json

'''
Program data global variables
'''
#backend
logger = None

#experiment data
webcam_num = 1
study_name = ''
study_files = []
subject_id_entry_box = None
experiment = None

#recording
window = None
recorder = None
just_started = True

#files
out_dir = None
video_path = None
video_id = None
last_video_id = None

#tk ui
main_frame = None
pop_up_window = None
width = 0
height = 0
key_tracker = None
padding_x = 10
padding_y = 10
default_font = 20

#Settings
settings_dict_defaults = {'backcolor': '#000000',
    'ui_element_color': '#888888',
    'forecolor': '#000000',
    'draggable_color0': '#888888',
    'draggable_color1': '#aaaaaa'}
settings_dict = {}


'''
Initialization
'''
def main():
    '''
    First method called in this thread of program execution.
    Runs through a servies of initialization steps and then loads the gui.
    Once the gui is loaded, the gui takes over control of program execution from there onwards.
    '''

    init_logging()
    load_config()
    init_gui()

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
    logger.info('init_logging: Starting log')

def load_config():
    '''
    Loads the user settings from the config.csv file. If the file is not pressent or is corrputed, it will use default values
    and write a new config file, overwritting the old one if it is present.
    '''

    global settings_dict

    logger.info('load_config:')

    try:
        with open('config.json', 'r') as config:
            settings_dict = json.loads(config.read())
    except Exception as err:
        message = 'load_config: Could not read config file'
        logger.error(message + ': ' + str(err))
        recover_config_file()

def recover_config_file():
    '''
    This method should only be called if the config file is corrupted or missing. It re-writes the config data and replaces all
    data with the default values, or the last loaded non-corrupt data value if such a data value is present.

    If this operations fails, the program will continue to run, but no config file will be generated.
    '''

    global settings_dict
    logger.info('recover_config_file: loading default settings and attempting to recover the config file')
    settings_dict = settings_dict_defaults
    try:
        with open('config.json', 'w') as config:
            print(json.dumps(settings_dict_defaults), file=config)
    except Exception as err:
        message = 'Attempt to recover config file failed: Could not write new config file' 
        logger.critical('recover_config_file:' + message + ': ' + str(err))
        pop_up(message)

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
        logger.info('find_webcams: ' + str(webcam_num) + ' webcams found for recording')

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

    logger.info('init_gui:')

    #Master window
    window = tk.Tk()
    window.wm_title('Sign Recorder')
    window.config(background = settings_dict['backcolor'])
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()
    window.geometry("%dx%d+0+0" % (width, height))

    #Main Frame in window
    main_frame = MainFrame(window, background = settings_dict['backcolor'])
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


'''
Core backend program functionality
'''
def pop_up(message):
    '''
    Creates a pop-up window to display a message. Please only call this method for important errors such as files that fail
    to load--each pop up will take focue from the main window and thus disrupt the user.
    '''

    global pop_up_window

    logger.info('pop_up: message=' + message)

    pop_up_window = tk.Tk()
    pop_up_window.wm_title('Message')
    pop_up_window.config(background = settings_dict['backcolor'])

    pop_up_text = tk.Text(pop_up_window, font = default_font, height = 5, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
    pop_up_text.insert(tk.INSERT, message)
    pop_up_text.config(state = 'disabled')
    pop_up_text.grid(row = 0, column = 0, padx = padding_x, pady = padding_y)

    select_files_button = tk.Button(pop_up_window, text ="Close", command = pop_up_window.destroy, font = default_font, height = 3, width = 10, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
    select_files_button.grid(row=1, column=0)

def write_out(name, message):
    '''
    Writes out a meta-file that contains metadata about the recorded video. The data is:
        stimulus_name: the name of the file used as a stimulus for this recording
        display_time: the amount of time the stimulus was displayed before recording
        recording_time: the time length of the recording
        total_time: the total time for this step of the experiment, = display_time + recording_time
    '''

    logger.info('write_out: writing meta file at path=' + out_dir + ' with name=' + name)
    file_name = os.path.join(out_dir, name + '.meta.csv')
    try:
        if os.path.exists(file_name):
            message = 'Cannot overwrite existing meta file: '
            logger.critical('write_out: ' + message + file_name)
            pop_up(message + '\n' + file_name)
            raise Exception(message + file_name)
        with open(file_name, 'w') as meta:
            print(message, file=meta)
    except Exception as err:
        message = 'Failed to write out file: ' + file_name
        logger.critical('write_out: ' + message + ': ' + str(err))
        pop_up(message)
        raise Exception(message)

def on_close(close = True):
    '''
    Handles properly closing the program and its spawned resources. As much as possible, all close events should be routed to
    this method rather than immediately calling an exit function.

    Parameter:
        close: Whether this method should close the program. If false, all program resources still will be cleared but the program
        will not be closed. This should be done when a critical exception occurs so the exception can still be raised.
    '''

    logger.info('on_close: Cleaning resources and closing' if close else 'on_close: Cleaning resources to prepare for closing')

    window.destroy()
    try:
        recorder.end()
    except:
        pass
    if close:
        sys.exit(0)


'''
Experiment and data collection
'''
def on_key_press(event):
    '''
    Called whenever a key press event is detected. This method should not be linked to key press events directly; the use of the
    KeyTracker class is necessary to authenticate key presses as valid before attempting to respond to them.

    If this program has just started, the program runs a different method to respond to the key press event to manage the yet
    un-initialized variables.
    '''

    experiment.on_input_press(event.keysym)

def on_key_release(event):
    '''
    Called whenever a key release event is detected. This method should not be linked to key release events directly; the use 
    of the KeyTracker class is necessary to authenticate key releases as valid before attempting to respond to them.
    '''

    experiment.on_input_release(event.keysym)

class Experiment(abc.ABC):
    @abc.abstractmethod
    def on_input_press(self, input_key):
        pass

    @abc.abstractmethod
    def on_input_release(self, input_key):
        pass

class Naming_Experiment(Experiment):
    #Experiment Parameters
    stimuli = []
    subject_id = None
    stimulus_type = None

    #Experiment Running
    recording = False
    last_video_id = None
    video_id = None
    keep_displaying = True
    current_stimulus = 0
    can_start_recording = True
    data = ''
    
    #Timing
    display_timer = None
    recording_timer = None

    def __init__(self, data):
        '''
        Creates a new Naming_Experiment, which is an experiemnt in which single stimuli are presented and the subject is asked to
        produce the sign for what is shown.

        Parameters:
            data: A dictionary containing experiment data. This should contain the follwoing keys:
                file, containing absolute paths to all of the stimuli to use;
                stimulus_type, which tells whether the stimulus is Image or Video

        '''
        self.stimuli = data['stimulus_files']
        self.stimulus_type = data['stimulus_type']
        self.display_timer = Timer()
        self.recording_timer = Timer()

    def on_input_press(self, input_key):
        '''
        This method should be called every time space is pressed (if that space-press has been authenticated). It proceeds
        to the next stimulus and will begin recording, ending the current stimulus and recording. It also ends the recording_timer if 
        it was running, and updates program state tracking variables to refect the current state of the progam.

        If there are no more stimuli to run, the program displays a pop-up message stating that data collection is complete.
        '''

        logger.info('Naming_Experiment: on_input_press: current_stimulus=' + str(self.current_stimulus) + ' recording=' + str(self.recording))
        self.recording = False
        if self.recording_timer.active():
            self.recording_timer.end()
            self.data += str(self.current_stimulus) + '_' + '_recordingTime,' + str(self.recording_timer.timespan) + '\n'
        if self.current_stimulus >= len(self.stimuli):
            message = 'All data for ' + str(self.subject_id) + ' has been collected'
            write_out(self.subject_id + '_timing.csv', self.data)
            pop_up(message)
            logger.info('Naming_Experiment: on_input_press: ' + message)
            main_frame.select_start_experiment()
            self.reset_for_next_subject()
        else:
            self.load_stimulus()

    def on_input_release(self, input_key):
        '''
        This method should be called when space is released (if that release has been authenticated). It begins recording and starts
        the recording timer. It also updates program state tracking variables to refect the current state of the progam.
        '''

        if self.subject_id == None:
            self.subject_id = subject_id_entry_box.get().strip()
        if self.can_start_recording and self.current_stimulus < len(self.stimuli):
            logger.info('Naming_Experiment: on_input_release: current_stimulus=' + str(self.current_stimulus) + '; recording starting')
            self.last_video_id = self.video_id
            self.video_id = os.path.basename(self.stimuli[self.current_stimulus].strip())
            self.recording = True
            self.keep_displaying = False
            self.recording_timer.begin()
            self.current_stimulus += 1
            recorder = Recorder(self.subject_id + '-' + self.video_id, True)
            recorder.begin()
        else:
            logger.warning('Naming_Experiment: on_input_release: can_start_recording is False, video must end before the signer may be recorded')

    def load_stimulus(self):
        '''
        Loads and displays the next stimulis for the current subject, but should not be used for the first stimulus of a subjecct.
        It resets the display timer, which measures the time that a stimulus is displayed before signing.

        Later, it will also write timer output to a meta file with the same name as the output file. Timer data it not yet verified
        though, so it is not ready for use.
        '''

        global keep_displaying
        logger.info('Naming_Experiment: load_stimulus: current_stimulus=' + str(self.current_stimulus) + ' stimulus type=' + str(self.stimulus_type))

        keep_displaying = True
        stimulus = self.stimuli[self.current_stimulus].strip()
        if self.display_timer.active():
            self.display_timer.end()
            self.data += str(self.current_stimulus) + '_' + '_displayTime,' + str(self.display_timer.timespan) + '\n'
        if self.stimulus_type == 'Image':
            self.display_timer.begin()
            Image_Displayer(stimulus).begin()
        elif self.stimulus_type == 'Video':
            self.display_timer.begin()
            Video_Displayer(stimulus).begin()

    def reset_for_next_subject(self):
        '''
        Resets the environment so that the next subject can begin the experiment.
        '''

        logger.info('Naming_Experiment: reset_for_next_subject: Resetting the environment for the next subject')

        key_tracker.reset()
        self.subject_id = None
        self.recording = False
        self.last_video_id = None
        self.video_id = None
        self.keep_displaying = True
        self.current_stimulus = 0
        self.can_start_recording = True
        subject_id_entry_box.delete(0, last='end')

class Lexical_Priming_Experiment(Experiment):
    #Experiment Parameters
    stimuli_tuples = []
    subject_id = None
    stimulus_type = None
    primer_type = None
    primer_time = 5

    #Experiment Running
    recording = False
    last_video_id = None
    video_id = None
    keep_displaying = True
    current_round = 0
    can_start_recording = True
    display_primer = True
    
    #Timing
    display_timer = None
    recording_timer = None
    primer_timer = None

    def __init__(self, data):
        '''
        Creates a new Lexical_Priming_Experiment, in which there is a primer image followed by a stimulus for signing. Recording begins
        after the stimulus has been shown. Transition between the primer and stimulus is done using space, as is transition between the
        stimulus and the recording, etc.

        Parameters:
            data: A dictionary containing experiment data. This should contain the follwoing keys:
                files, which contains a tuple of: (absolute path of the primer, that of the stimulus);
                stimulus_type, which tells whether the stimulus is Image or Video;
                primer_type, which tells whether the primer is Image or Video;
                primer_time, which contains the time to show the primer (in seconds, only needed if primer_time is Image)

        '''
        self.stimuli_tuples = data['files']
        self.stimulus_type = data['stimulus_type']
        self.primer_type = data['primer_type']
        self.primer_time = data['primer_time'] if self.primer_type == 'Image' else 0
        self.display_timer = Timer()
        self.recording_timer = Timer()
        self.prim_timers = Timer()

    def on_input_press(self, input_key):
        '''
        This method should be called every time space is pressed (if that press has been authenticated), except the first. It proceeds
        to the next stimulus and will begin recording, ending the current stimulus and recording. It also ends the recording_timer if 
        it was running, and updates program state tracking variables to refect the current state of the progam.

        If there are no more stimuli to run, the program displays a pop-up message stating that data collection is complete.
        '''
        logger.info('Lexical_Priming_Experiment: on_input_press: current_stimulus=' + str(self.current_round) + ' recording=' + str(self.recording) + ', display_primer=' + self.display_primer)
        if self.display_primer:
            pass
        else:
            
            self.recording = False
            if self.recording_timer.active():
                self.recording_timer.end()
            if self.current_round >= len(self.stimuli_tuples):
                main_frame.select_start_experiment()
                pop_up('All data for ' + self.subject_id + ' has been collected')
                self.reset_for_next_subject()
            else:
                self.load_primer()

    def on_input_release(self, input_key):
        '''
        This method should be called when space is released (if that release has been authenticated). It begins recording and starts
        the recording timer. It also updates program state tracking variables to refect the current state of the progam.
        '''

        if self.display_primer:
            self.display_primer = False
            #code here
        else:
            if self.subject_id == None:
                self.subject_id = subject_id_entry_box.get().strip()
            if self.can_start_recording and self.current_round < len(self.stimuli_tuples):
                logger.info('Lexical_Priming_Experiment: on_input_release: current_round=' + str(self.current_round) + '; recording starting')
                self.last_video_id = self.video_id
                self.video_id = os.path.basename(self.stimuli_tuples[self.current_round][0].strip()) + '-' + os.path.basename(self.stimuli_tuples[self.current_round][1].strip())
                self.recording = True
                self.keep_displaying = False
                self.recording_timer.begin()
                self.current_round += 1
                recorder = Recorder(self.subject_id + '-' + self.video_id, True)
                recorder.begin()
            else:
                logger.warning('Naming_Experiment: on_input_release: can_start_recording is False, video must end before the signer may be recorded')

    def load_primer(self): #WHat about stimuli?
        '''
        Loads and displays the next stimulus for the current subject, but should not be used for the first stimulus of a subjecct.
        It resets the display timer, which measures the time that a stimulus is displayed before signing.

        Later, it will also write timer output to a meta file with the same name as the output file. Timer data it not yet verified
        though, so it is not ready for use.
        '''

        global keep_displaying
        logger.info('Lexical_Priming_Experiment: load_stimulus: current_stimulus=' + str(self.current_round) + ' stimulus type=' + str(self.stimulus_type))

        keep_displaying = True
        primer = self.stimuli_tuples[self.current_round][0].strip()
        timer = None
        if self.display_timer.active():
            self.display_timer.end()
        if self.primer_type == 'Image':
            self.display_timer.begin()
            Image_Displayer(primer).begin()
            timer = threading.Timer(self.primer_time, self.on_primer_finished) #In seconds
        elif self.primer_type == 'Video':
            self.display_timer.begin()
            Video_Displayer(primer).begin()
            timer = threading.Timer(self.primer_time, self.on_primer_finished) #In seconds
        timer.start()

    def on_primer_finished(self):
        stimulus = self.stimuli_tuples[self.current_round][1].strip()
        if self.stimulus_type == 'Image':
            self.display_timer.begin()
            Image_Displayer(stimulus).begin()
        elif self.stimulus_type == 'Video':
            self.display_timer.begin()
            Video_Displayer(stimulus).begin()

    def reset_for_next_subject(self):
        '''
        Resets the environment so that the next subject can begin the experiment.
        '''

        logger.info('Lexical_Priming_Experiment: reset_for_next_subject: Resetting the environment for the next subject')

        key_tracker.reset()
        self.subject_id = None
        self.recording = False
        self.last_video_id = None
        self.video_id = None
        self.keep_displaying = True
        self.current_stimulus = 0
        self.can_start_recording = True
        subject_id_entry_box.delete(0, last='end')


'''
Data and user-input
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

        logger.info('Recorder: __init__: name=' + self.name + ' mirror=' + str(mirror))
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
        if os.path.exists(file_name):
            message = 'Cannot overwrite existing video file: ' 
            logger.critical('Recorder: begin: ' + message + file_name)
            pop_up(message + '\n' + file_name)
            raise Exception(message + file_name)
        else:
            self.video_writer = cv2.VideoWriter(file_name, fourcc, fps, (width, height))

        if not self.web_cam.isOpened():
            message = 'Could not open webcam'
            logger.warning('Recorder: begin: ' + message)
            pop_up(message)
            raise Exception(message)
    
        logger.info('Recorder: begin: starting recording loop')
        while self.web_cam.isOpened():
            # Capture frame-by-frame
            is_reading, frame = self.web_cam.read()
    
            if is_reading and experiment.recording:
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self.video_writer.write(frame)
            else:
                break
    
            if cv2.waitKey(1) & 0xFF == ord('1'): #quit on 1
                experiment.on_input_release('space')
                break
    
        self.end()
    
    def end(self):
        '''
        Ends the recording and releases resources.
        '''

        logger.info('Recorder: end: recording ended, releasing resources')
        self.web_cam.release()
        self.video_writer.release()

class Video_Displayer():
    file_name = ''
    video_input = None
    fps = None
    display = None
    callback = None

    def __init__(self, file_name, callback = None):
        logger.info('Video_Displayer: __init__: file_name=' + file_name)
        self.file_name = file_name
        self.callback = callback

    def begin(self):
        experiment.can_start_recording = False
        self.video_input = cv2.VideoCapture(self.file_name)
        self.fps = int(self.video_input.get(cv2.CAP_PROP_FPS))
        self.display = main_frame.page_show_stimuli.display_region
        logger.info('Video_Displayer: begin: ' + self.file_name + ' running at fps=' + str(int(self.fps)))

        if not self.video_input.isOpened():
            message = 'Could not open video file for reading'
            logger.warning('Video_Displayer: begin: ' + message)
            pop_up(message)
            raise Exception(message)

        main_frame.select_show_stimuli()
        self.run_frame()        

    def run_frame(self):
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
                self.end('Video_Displayer: run_frame: display ended due to unexpected closure of video_input')
                experiment.can_start_recording = True
                if not self.callback == None:
                    self.callback()
        else:
            self.end('Video_Displayer: run_frame: display ended naturally')
            experiment.can_start_recording = True
            if not self.callback == None:
                self.callback()
            

    def end(self, message = 'Video_Displayer: end: run_frame ended'):
        logger.info(message)
        self.video_input.release()
        if not self.callback == None:
            self.callback()

class Image_Displayer():
    file_name = ''
    display = None

    def __init__(self, file_name):
        logger.info('Image_Displayer: __init__: ' + file_name)
        self.file_name = file_name

    def begin(self):
        logger.info('Image_Displayer: begin:')
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
        logger.info('KeyTracker: track: key=' + key)
        self.key = key

    def reset(self):
        logger.info('KeyTracker: reset: resetting')
        self.last_press_time = 0
        self.last_release_time = 0
        self.last_release_callback_time = 0
        self.first_callback_call = True
        self.last_event_was_press = False

    def is_pressed(self):
        return time.time() - self.last_press_time < .01 #In seconds

    def report_key_press(self, event):
        if not self.last_event_was_press and event.keysym == self.key:
            self.last_event_was_press = True
            if not self.is_pressed():
                logger.info('KeyTracker: report_key_press: valid keypress detected: key=' + self.key)
                self.last_press_time = time.time()
                on_key_press(event)
            else:
                self.last_press_time = time.time()

    def report_key_release(self, event):
        if self.last_event_was_press and event.keysym == self.key:
            self.last_event_was_press = False
            self.last_release_time = time.time()
            timer = threading.Timer(.015, self.report_key_release_callback, args=[event]) #In seconds
            timer.start()
    
    def report_key_release_callback(self, event):
        if self.first_callback_call:
            self.last_release_callback_time = time.time()
            self.first_callback_call = False
        if not self.is_pressed():
            self.last_release_callback_time = time.time()
            logger.info('KeyTracker: report_key_release_callback: key=' + self.key + ', is released= ' + str((not self.is_pressed())))
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
UI and layout management
'''
def arrange_header_in(page):
    button_frame = page.button_frame
    top_bar_buttons = []
    #Place buttons in the top-level button frame
    top_bar_buttons.append(tk.Button(button_frame, text="Main Menu", font=default_font, command=main_frame.select_main_menu, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor']))
    top_bar_buttons.append(tk.Button(button_frame, text="Create Experiment", font=default_font, command=main_frame.select_create_experiment, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor']))
    top_bar_buttons.append(tk.Button(button_frame, text="Start Experiment", font=default_font, command=main_frame.select_start_experiment, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor']))
    
    #Grid buttons
    col = 0
    for button in top_bar_buttons:
        button.grid(row=0, column=col, pady=10)
        col += 1

    button_frame.grid(row=0, column=0)

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

class Widget_Drag_Controller():
    '''
    This class handles dragging widgets that below to a common set in such a way as to change their positions in that set. So if the numbers
    1, 2, 3 are shown on screen, it's goal is to allow you to click on, say, the 3 and move it in from of the one, and then to read back that
    array in the new order.
    '''
    item = None
    callback = None
    move_frame = None

    def __init__(self, item, widgets, callback):
        '''
        Parameters:
            item: The specific item out of the set that can be dragged
            widgets: The set of all widgets that are ordered on the screen and can be dragged
            callback: the function to call after a drag and drop. It should accept a list of files in the new order as a parameter.
        '''

        self.item = item
        self.widgets = widgets
        self.callback = callback

        #Bind clicks on the item itself
        self.item.bind("<ButtonPress-1>", self.on_start)
        self.item.bind("<B1-Motion>", self.on_move)
        self.item.bind("<ButtonRelease-1>", self.on_end)

        self.item.configure(cursor="hand1")

    def on_start(self, event):
        print('on_start')
        self.last_seen = self.item
        self.move_frame = tk.Frame()
        tk.Label(self.move_frame, text = self.item.cget('text'), font = self.item.cget('font'), anchor = self.item.cget('anchor'), background = self.item.cget('background')).pack(side = 'top', fill = 'x')

    def on_move(self, event):
        print('on_move')
        x, y = event.widget.winfo_pointerxy()
        self.move_frame.place(x = x, y = int(y - (self.item.winfo_height() + self.item.winfo_height() / 2)))

    def on_end(self, event):
        print('on_end')
        self.move_frame.destroy()
        x, y = event.widget.winfo_pointerxy()
        target = event.widget.winfo_containing(x, y)

        move_to = self.widgets.index(target)
        move_from = self.widgets.index(self.item)

        if move_to > move_from:
            self.widgets.insert(move_to + 1, self.item)
            del self.widgets[move_from]
        elif move_to < move_from:
            self.widgets.insert(move_to, self.item)
            del self.widgets[move_from + 1]

        files = [widget.cget('text') for widget in self.widgets]
        self.callback(files)
        
class File_Arrangement_Region():
    canvas = None
    display_frame = None
    elements = []
    width = 0
    height = 0
    owner = None
    widget_drag_controllers = []
    owner_update_callback = None

    def __init__(self, owner, owner_update_callback, root, width, height, row, column, rowspan = 1, columnspan = 1):
        self.owner_update_callback = owner_update_callback
        self.width = width
        self.height = height
        self.owner = owner

        outer_frame = tk.Frame(root, background = settings_dict['ui_element_color'])
        outer_frame.grid(row = row, column = column, rowspan = rowspan, columnspan = columnspan, padx=padding_x, pady=padding_y)

        self.canvas = tk.Canvas(outer_frame, background = settings_dict['ui_element_color'])
        self.display_frame = tk.Frame(self.canvas, background = settings_dict['ui_element_color'])
        scrollbar_y = tk.Scrollbar(outer_frame, orient = 'vertical',command = self.canvas.yview)
        scrollbar_x = tk.Scrollbar(outer_frame, orient = 'horizontal',command = self.canvas.xview)
        self.canvas.configure(yscrollcommand = scrollbar_y.set)
        self.canvas.configure(xscrollcommand = scrollbar_x.set)

        scrollbar_y.pack(side = 'right',fill = 'y')
        scrollbar_x.pack(side = 'bottom', fill = 'x')
        self.canvas.pack(side = 'left')
        self.canvas.create_window((0, 0), window = self.display_frame, anchor = 'nw')
        self.display_frame.bind('<Configure>', self.scroll_configure)
    
    def scroll_configure(self, event):
        self.canvas.configure(scrollregion = self.canvas.bbox('all'), width = self.width, height = self.height)

    def set_elements(self, files):
        #Remove old elements
        self.widget_drag_controllers.clear()
        for child in self.display_frame.winfo_children():
            child.destroy()

        #Add new elements (OLD)
        for i in range(len(files)):
            highlight = settings_dict['draggable_color' + str(i % 2)]
            tk.Label(self.display_frame, text=files[i], font = default_font, anchor = 'w', background = highlight).pack(side = 'top', fill = 'x')
        for label in self.display_frame.winfo_children():
            print(label);
            self.widget_drag_controllers.append(Widget_Drag_Controller(label, self.display_frame.winfo_children(), self.update_owner_data))

        '''#Add new elements
        for i in range(len(files)):
            highlight = settings_dict['draggable_color' + str(i % 2)]
            container = tk.Frame(self.display_frame, width = width, height = int(height / 1.25), background = highlight)

            label = tk.Label(container, text=files[i], font = default_font, anchor = 'w', background = highlight)
            label.pack(side = 'left')

            remove_button = tk.Button(container, text ="-", command = self.on_button_remove, font = default_font, height = 1, width = 3, background = highlight, foreground = settings_dict['forecolor'])
            remove_button.pack(side = 'right')
            
            label.bindtags(("draggable",) + label.bindtags())

            container.pack(side = 'top', fill = 'x')
        for element in self.display_frame.winfo_children():
            print(element);
            self.widget_drag_controllers.append(Widget_Drag_Controller(element, self.display_frame.winfo_children(), self.update_owner_data))'''
    
    def on_button_remove(self):
        pass
            
    def update_owner_data(self, files):
        self.owner_update_callback(files)

class Page(tk.Frame):
    button_frame = None

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.button_frame = tk.Frame(self, background = settings_dict['backcolor'])

    def show(self):
        print('Show')
        print(self)
        self.lift()

class Page_Main_Menu(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):

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

        file_text = tk.Text(self, font = default_font, height = 15, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        file_text.insert(tk.INSERT, about_text)
        file_text.config(state = 'disabled')
        file_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

class Page_Naming_Paradigm(Page):
    file_arrangement_region = None
    stimulus_option_selected = None
    num_rows = 0

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):
        stimulus_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        stimulus_text.insert(tk.INSERT, '\nSelect Stimulus Type')
        stimulus_text.tag_configure("center", justify='center')
        stimulus_text.tag_add("center", 1.0, "end")
        stimulus_text.config(state = 'disabled')
        stimulus_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        stimulus_options = ['Video', 'Image']
        stimulus_default_option = stimulus_options[0]
        self.stimulus_option_selected = tk.StringVar(self)
        stimulus_option_menu = tk.OptionMenu(self, self.stimulus_option_selected, *stimulus_options)
        self.stimulus_option_selected.set(stimulus_default_option)
        stimulus_option_menu.config(background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'], height = 1, width = 30, font = default_font)
        stimulus_option_menu.grid(row=1, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        select_files_button = tk.Button(self, text ="Select Stimulus Files", command = self.load_files, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        select_files_button.grid(row=2, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        self.file_arrangement_region = File_Arrangement_Region(self, self.change_files, self, width / 2, height / 1.5, 0, 1, 20)
        self.file_arrangement_region.set_elements(['Selected Files:'])

    def load_files(self):
        logger.info('Page_Naming_Paradigm: load_files: loading files')
        self.files = filedialog.askopenfilenames(parent=self, initialdir="/", title='Select Files' + self.stimulus_option_selected.get() + ' files')
        display_strs = self.files
        self.file_arrangement_region.set_elements(display_strs)

    def change_files(self, files):
        self.files = files
        self.file_arrangement_region.set_elements(self.files)

    def dict_data(self):
        data = {}
        data['paradigm'] = 'Naming'
        data['stimulus_type'] = self.stimulus_option_selected.get()
        data['stimulus_files'] = self.files
        return data

class Page_Lexical_Priming(Page):
    stimulus_file_arrangement_region = None
    primer_file_arrangement_region = None
    stimulus_option_selected = None
    primer_option_selected = None
    stimulus_files = []
    primer_files = []
    num_rows = 0

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):
        stimulus_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        stimulus_text.insert(tk.INSERT, '\nSelect Stimulus Type')
        stimulus_text.tag_configure("center", justify='center')
        stimulus_text.tag_add("center", 1.0, "end")
        stimulus_text.config(state = 'disabled')
        stimulus_text.grid(row=0, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        stimulus_options = ['Video', 'Image']
        stimulus_default_option = stimulus_options[0]
        self.stimulus_option_selected = tk.StringVar(self)
        stimulus_option_menu = tk.OptionMenu(self, self.stimulus_option_selected, *stimulus_options)
        self.stimulus_option_selected.set(stimulus_default_option)
        stimulus_option_menu.config(background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'], height = 1, width = 30, font = default_font)
        stimulus_option_menu.grid(row=1, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        primer_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        primer_text.insert(tk.INSERT, '\nSelect Primer Type')
        primer_text.tag_configure("center", justify='center')
        primer_text.tag_add("center", 1.0, "end")
        primer_text.config(state = 'disabled')
        primer_text.grid(row=2, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        primer_options = ['Video', 'Image']
        primer_default_option = primer_options[0]
        self.primer_option_selected = tk.StringVar(self)
        primer_option_menu = tk.OptionMenu(self, self.primer_option_selected, *primer_options)
        self.primer_option_selected.set(primer_default_option)
        primer_option_menu.config(background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'], height = 1, width = 30, font = default_font)
        primer_option_menu.grid(row=3, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        stimulus_select_files_button = tk.Button(self, text ="Select Stimulus Files", command = self.load_stimulus_files, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        stimulus_select_files_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        self.stimulus_file_arrangement_region = File_Arrangement_Region(self, self.change_stimulus_files, self, width / 4, height / 1.5, 0, 1, 20)
        self.stimulus_file_arrangement_region.set_elements(['Selected Files:'])

        primer_select_files_button = tk.Button(self, text ="Select Primer Files", command = self.load_primer_files, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        primer_select_files_button.grid(row=5, column=0, padx=padding_x, pady=padding_y)
        self.num_rows += 1

        self.primer_file_arrangement_region = File_Arrangement_Region(self, self.change_primer_files, self, width / 4, height / 1.5, 0, 2, 20)
        self.primer_file_arrangement_region.set_elements(['Selected Files:'])

    def load_stimulus_files(self):
        self.load_files(True)

    def load_primer_files(self):
        self.load_files(False)

    def load_files(self, is_stimulus):
        logger.info('Page_Lexical_Priming: load_files: loading files, is_stimulus=' + str(is_stimulus))
        if is_stimulus:
            self.stimulus_files = filedialog.askopenfilenames(parent=self, initialdir="/", title='Select Stimulus Files' + self.stimulus_option_selected.get() + ' files')
            self.stimulus_file_arrangement_region.set_elements(self.stimulus_files)
        else:
            self.primer_files = filedialog.askopenfilenames(parent=self, initialdir="/", title='Select Primer Files' + self.primer_option_selected.get() + ' files')
            self.primer_file_arrangement_region.set_elements(self.primer_files)

    def change_stimulus_files(self, files):
        self.stimulus_files = files
        self.stimulus_file_arrangement_region.set_elements(self.stimulus_files)

    def change_primer_files(self, files):
        self.primer_files = files
        self.primer_file_arrangement_region.set_elements(self.primer_files)

    def dict_data(self):
        primers = self.primer_option_selected.get()
        stimuli = self.stimulus_files

        if len(primers) != len(stimuli):
            message = 'Cannot write file: There must be a 1:1 mapping of primers to stimuli'
            logger.warning('Page_Lexical_Priming: dict_data: ' + message)
            pop_up(message)
            return []

        data = {}
        data['paradigm'] = 'Lexical_Priming'
        data['files'] = [(primer, stimulus) for primer in primers for stimulus in stimuli]
        data['stimulus_type'] = self.stimulus_option_selected.get()
        return data

class Page_Create_Experiment(Page):
    files = []
    option_selected = None
    paradigm_option_selected = None
    entry = None
    selected_files_info_text = None
    page_naming_paradigm = None
    page_lexical_priming = None
    create_experiment_button = None

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()
        
    def init_elements(self):
        arrange_header_in(self)

        self.page_naming_paradigm = Page_Naming_Paradigm(self, background = settings_dict['backcolor'])
        self.page_lexical_priming = Page_Lexical_Priming(self, background = settings_dict['backcolor'])

        paradigm_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        paradigm_text.insert(tk.INSERT, '\nSelect Experiemnt Paradigm')
        paradigm_text.tag_configure("center", justify='center')
        paradigm_text.tag_add("center", 1.0, "end")
        paradigm_text.config(state = 'disabled')
        paradigm_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        paradigm_options = ['Naming', 'Lexcial Priming']
        default_paradigm_option = paradigm_options[0]
        self.paradigm_option_selected = tk.StringVar(self)
        self.paradigm_option_selected.trace('w', self.paradigm_selected)
        paradigm_option_menu = tk.OptionMenu(self, self.paradigm_option_selected, *paradigm_options)
        self.paradigm_option_selected.set(default_paradigm_option)
        paradigm_option_menu.config(background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'], height = 1, width = 30, font = default_font)
        paradigm_option_menu.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        #Container
        container = tk.Frame(self, width = width, height = int(height / 1.25), background = settings_dict['backcolor'])
        container.grid(row=3, column=0, rowspan = 10, columnspan = 400, padx=0, pady=padding_y)

        #Place pages in the container frame
        self.page_naming_paradigm.place(in_=container)
        self.page_lexical_priming.place(in_=container)

        paradigm_option_string = self.paradigm_option_selected.get()
        if paradigm_option_string == 'Naming':
            self.page_naming_paradigm.show()
        elif paradigm_option_string == 'Lexcial Priming':
            self.page_lexical_priming.show()

        #Create Experiment Button
        self.create_experiment_button = tk.Button(self, text ="Create Experiment", command = self.create_experiment, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        self.create_experiment_button.grid(row = 1, column = 1, padx = padding_x, pady = padding_y)

    def create_experiment(self):
        logger.info('Page_Create_Experiment: create_experiment: creating experiment')

        paradigm_option_string = self.paradigm_option_selected.get()
        exp_data = None
        if paradigm_option_string == 'Naming':
            exp_data = self.page_naming_paradigm.dict_data()
        elif paradigm_option_string == 'Lexcial Priming':
            exp_data = self.page_lexical_priming.dict_data()
        
        data = {}
        data['paradigm'] = paradigm_option_string
        data.update(exp_data)

        try:
            experimant_name = filedialog.asksaveasfilename(initialdir = "/", title = "Save file", filetypes = (("experiment files","*.exp"), ("all files","*.*")))
            with open(experimant_name, 'w') as experiment:
                print(json.dumps(data), file=experiment)
        except Exception as err:
            message = 'Error: Could not write experiment file'
            logger.error('Page_Create_Experiment: create_experiment: ' + message + ': ' + str(err))
            pop_up(message)

    def paradigm_selected(self, name, index, mode):
        paradigm_option_string = self.paradigm_option_selected.get()
        logger.info('Page_Create_Experiment: paradigm_selected: paradigm_option_string=' + paradigm_option_string)
        
        if paradigm_option_string == 'Naming':
            pass
            #self.page_naming_paradigm.lift()
            #self.page_lexical_priming.lower()
        elif paradigm_option_string == 'Lexcial Priming':
            pass
            #self.page_lexical_priming.lift()
            #self.page_naming_paradigm.lower()

class Page_Start_Experiment(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.init_elements()

    def init_elements(self):
        global subject_id_entry_box

        arrange_header_in(self)

        file_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        file_text.insert(tk.INSERT, '\nSelect an experiment file to load')
        file_text.tag_configure("center", justify='center')
        file_text.tag_add("center", 1.0, "end")
        file_text.config(state = 'disabled')
        file_text.grid(row=1, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose file", command = self.load_experiment, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        select_file_button.grid(row=2, column=0, padx=padding_x, pady=padding_y)

        dir_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        dir_text.insert(tk.INSERT, '\nSelect a folder in which to save the output')
        dir_text.tag_configure("center", justify='center')
        dir_text.tag_add("center", 1.0, "end")
        dir_text.config(state = 'disabled')
        dir_text.grid(row=3, column=0, padx=padding_x, pady=padding_y)

        select_file_button = tk.Button(self, text ="Choose output folder", command = self.load_dir, font = default_font, height = 1, width = 30, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        select_file_button.grid(row=4, column=0, padx=padding_x, pady=padding_y)

        entry_text = tk.Text(self, font = default_font, height = 3, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        entry_text.insert(tk.INSERT, '\nEnter subject ID')
        entry_text.tag_configure("center", justify='center')
        entry_text.tag_add("center", 1.0, "end")
        entry_text.config(state = 'disabled')
        entry_text.grid(row=5, column=0, padx=padding_x, pady=padding_y)

        subject_id_entry_box = tk.Entry(self, font = default_font, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        subject_id_entry_box.grid(row=6, column=0, padx=padding_x, pady=padding_y)

        how_to_string = '''
        When you are ready to begin the experiment, press the space bar. 

        Once you are ready to sign based on what you see, press the space
        bar to start recording.

        Once you are done signing, press the space bar again. You will then
        see the next prompt and the program will begin recording.
        '''
        how_to_text = tk.Text(self, font = default_font, height = 9, width = 70, background = settings_dict['ui_element_color'], foreground = settings_dict['forecolor'])
        how_to_text.insert(tk.INSERT, how_to_string)
        how_to_text.config(state = 'disabled')
        how_to_text.grid(row=7, column=0, padx=padding_x, pady=padding_y)

    def load_dir(self):
        global out_dir
        logger.info('Page_Start_Experiment: load_dir: loading save folder')
        try:
            out_dir = filedialog.askdirectory(parent = self, initialdir="/", title='Select Save Folder')
        except Exception as err:
            message = 'Could not load the selected directory'
            logger.error('Page_Start_Experiment: load_dir: ' + message + ': ' + str(err))
            pop_up(message)

    def load_experiment(self):
        global experiment
        logger.info('Page_Start_Experiment: load_experiment: loading experiment')
        experiment_file = filedialog.askopenfilename(parent=self, initialdir="/", title='Select Experiment')
        try:
            with open(experiment_file, 'r') as experiment_data:
                data = json.loads(experiment_data.read())
                if data['paradigm'] == 'Naming':
                    experiment = Naming_Experiment(data)
                elif data['paradigm'] == 'Lexical Priming':
                    pass
        except Exception as err:
            message = 'Could not load experiment file'
            logger.error('Page_Start_Experiment: load_experiment:' + message + ': ' + str(err))
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
        #self.buttonframe = tk.Frame(main_frame, background = settings_dict['backcolor'])
        self.config(background = settings_dict['backcolor'])

    def prepare_display(self):
        #Pages
        self.page_main_menu = Page_Main_Menu(self, width = width, height = height, background = settings_dict['backcolor'])
        self.page_create_experiment = Page_Create_Experiment(self, width = width, height = height, background = settings_dict['backcolor'])
        self.page_start_experiment = Page_Start_Experiment(self, width = width, height = height, background = settings_dict['backcolor'])
        self.page_show_stimuli = Page_Show_Stimuli(self, width = width, height = height, background = settings_dict['backcolor'])

        #Container
        container = tk.Frame(self, background = settings_dict['backcolor'])
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

The logger is not used here since, among the possible errors that could cause a crash is the logger not having write permissions
and it is still important the the failure be printed to a readable output.
'''
try:
    main()
except Exception as e:
    trace = traceback.format_exc()
    print('Something bad happened ' + str(e) + '\n' + str(trace))
    on_close(False)
    raise