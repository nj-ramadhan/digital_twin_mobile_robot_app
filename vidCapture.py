import cv2
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def grab_frame(cap):
    ret,frame = cap.read()
    return cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

#Initiate the two cameras
cap1 = cv2.VideoCapture(1)
cap1.set(cv2.CAP_PROP_FRAME_WIDTH,320)
cap1.set(cv2.CAP_PROP_FRAME_HEIGHT,240)
# cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
# cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap1.set(cv2.CAP_PROP_FPS, 30)
cap1.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
# cap2 = cv2.VideoCapture(1)

#create two subplots
ax1 = plt.subplot(1,1,1)
# ax2 = plt.subplot(1,2,2)

#create two image plots
im1 = ax1.imshow(grab_frame(cap1))
# im2 = ax2.imshow(grab_frame(cap2))

def update(i):
    im1.set_data(grab_frame(cap1))
    # im2.set_data(grab_frame(cap2))
    
#... other code
ani = FuncAnimation(plt.gcf(), update, interval=200)

def close(event):
    if event.key == 'q':
        plt.close(event.canvas.figure)

cid = plt.gcf().canvas.mpl_connect("key_press_event", close)

plt.show()

# code that should be executed after window is closed.