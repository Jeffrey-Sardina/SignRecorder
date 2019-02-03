import tkinter as tk

#text
default_font = 20

controls_text = '''
Space: start / stop recording
Enter: next stimulus / subject
Escape: quit
'''

about_text = '''Version: 0.1
Developer: Jeffrey Sardina 

SignRecorder is a simple program for recording and saving 
video '.avi' files for sign language data collection and
experiments. It is currently hosted on GitHub
(https://github.com/Jeffrey-Sardina/SignRecorder)
as an open-source project.
'''

into_text = '''To get started, click on either 'Create Experiemnt' or 
'Start Experiment'. The program will guide you through
loading stimuli and experimental methods. Once you have
made an experiemnt, save it so that you can load it later.
'''

class Page(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
    def show(self):
        self.lift()

class Page_Main_Menu(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        label = tk.Label(self, text=about_text + '\n\n' + into_text, justify='left', font = default_font)
        label.pack(side="top")

class Page_Create_Experiment(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        label = tk.Label(self, text="Seo é an dara leathnach")
        label.pack(side="top")

class Page_Start_Experiment(Page):
   def __init__(self, *args, **kwargs):
       Page.__init__(self, *args, **kwargs)
       label = tk.Label(self, text="Este es la tercera página")
       label.pack(side="top")

class MainFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        page_main_menu = Page_Main_Menu(self)
        page_create_experiment = Page_Create_Experiment(self)
        page_start_experiment = Page_Start_Experiment(self)

        buttonframe = tk.Frame(self)
        container = tk.Frame(self)
        buttonframe.pack(side="top", fill="x", expand=False)
        container.pack(side="top", fill="both", expand=True)

        page_main_menu.place(in_=container)
        page_create_experiment.place(in_=container)
        page_start_experiment.place(in_=container)

        b1 = tk.Button(buttonframe, text="Main Menu", font=default_font, command=page_main_menu.lift)
        b2 = tk.Button(buttonframe, text="Create Experiment", font=default_font, command=page_create_experiment.lift)
        b3 = tk.Button(buttonframe, text="Start Experiment", font=default_font, command=page_start_experiment.lift)

        b1.pack(side="left")
        b2.pack(side="left")
        b3.pack(side="left")

        page_main_menu.show()

if __name__ == "__main__":
    window = tk.Tk()
    main_frame = MainFrame(window)
    main_frame.pack(side="top", fill="both", expand=True)
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()
    window.geometry("%dx%d+0+0" % (width, height))
    window.mainloop()