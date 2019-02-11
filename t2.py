import cv2
import tkinter as tk
from PIL import Image, ImageTk


def test():
    # Load an color image
    img = cv2.imread('C:/Users/jeffr/Documents/Standard Documents/Programming/Projects/VS Code DEV/SignRecorder/test_files/test_images/Blue.png')

    #Rearrang the color channel
    b,g,r = cv2.split(img)
    img = cv2.merge((r,g,b))
    im = Image.fromarray(img)

    # Convert the Image object into a TkPhoto object
    imgtk = ImageTk.PhotoImage(image=im) 

    # Put it in the display window
    tk.Label(root, image=imgtk, borderwidth=0, highlightthickness=0).pack() 

# A root window for displaying objects
root = tk.Tk()  
test()
#root.after(1000, test)
root.mainloop() # Start the GUI

