import numpy as np
import time
import math
import cv2
import cv2.aruco as aruco
import imutils 
import os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from kivy.properties import ObjectProperty
from kivy.properties import StringProperty

colors = {
    "Blue": {
        "200": "#11619e",
        "500": "#11619e",
        "700": "#11619e",
    },

    "BlueGray": {
        "200": "#888888",
        "500": "#888888",
        "700": "#888888",
    },

    "Light": {
        "StatusBar": "#E0E0E0",
        "AppBar": "#202020",
        "Background": "#EEEEEE",
        "CardsDialogs": "#FFFFFF",
        "FlatButtonDown": "#CCCCCC",
    },

    "Dark": {
        "StatusBar": "#101010",
        "AppBar": "#E0E0E0",
        "Background": "#111111",
        "CardsDialogs": "#000000",
        "FlatButtonDown": "#333333",
    },
}

SETPOINT_COORD = np.array([[317.8, 406.795],[317.8, 242.2],[317.8, 77.606],
                           [175.257, 324.497],[175.257, 159.903],
                           [460.343, 324.497],[460.343, 159.903]])
TOLERANCE = 25.0

class ScreenSplash(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    app_window = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(ScreenSplash, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_progress_bar, .01)

    def update_progress_bar(self, *args):
        if (self.ids.progress_bar.value + 1) < 100:
            raw_value = self.ids.progress_bar_label.text.split('[')[-1]
            value = raw_value[:-2]
            value = eval(value.strip())
            new_value = value + 1
            self.ids.progress_bar.value = new_value
            self.ids.progress_bar_label.text = 'Loading.. [{:} %]'.format(new_value)
        else:
            self.ids.progress_bar.value = 100
            self.ids.progress_bar_label.text = 'Loading.. [{:} %]'.format(100)
            self.screen_manager.current = 'screen_main'
            return False

class ScreenMain(MDBoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenMain, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)
        Clock.schedule_interval(self.reguler_check, 1)
        self.coordinatesList = [[0, 0], [200, 200], [120, 250]]
        self.coordinatesList_prev = self.coordinatesList

    def delayed_init(self, dt):
        self.cap = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            print("Error: Unable to access the camera")
            return

        self.augDic = self.loadImages("markers")
        self.frames = {}
        self.prev_frames = {}
        self.prev_times = {}
        self.pixels_to_cm = 0.1 # Sesuaikan dengan informasi fisik dari ArUco marker atau objek yang digunakan
        # self.update_interval = 0.5  # Interval pembacaan kecepatan (dalam detik)
        # self.ids.layout_image.add_widget(FigureCanvasKivyAgg(self.fig))    

    def loadImages(self, path):
        mylist = os.listdir(path)
        noOfMarkers = len(mylist)
        print("Total Number of Markers detected:", noOfMarkers)
        augDic = {}
        for imgPath in mylist:
            key = int(os.path.splitext(imgPath)[0])
            imgAug = cv2.imread(f'{path}/{imgPath}')
            augDic[key] = imgAug
        return augDic

    def findArucoMarkers(self, img, draw=True):
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
        aruco_param =  aruco.DetectorParameters()
        bboxs, ids, rejected = aruco.detectMarkers(imgGray, aruco_dict, parameters=aruco_param)
        if draw and ids is not None:
            aruco.drawDetectedMarkers(img, bboxs)
        return [bboxs, ids]

    def augmentAruco(self, bbox, id, img, imgAug, drawId=True):
        tl = bbox[0][0]
        tr = bbox[0][1]    
        br = bbox[0][2]
        bl = bbox[0][3]
        h, w, c = imgAug.shape
        pts1 = np.array([tl, tr, br, bl])
        pts2 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        matrix, _ = cv2.findHomography(pts2, pts1)
        imgOut = cv2.warpPerspective(imgAug, matrix, (img.shape[1], img.shape[0]))
        cv2.fillConvexPoly(img, pts1.astype(int), (0, 0, 0))
        imgOut = img + imgOut

        if drawId:
            cv2.putText(imgOut, str(id), tl, cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 2)

        return imgOut

    def distance(self, p1, p2):
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def distance_cm(self, p1, p2, pixels_to_cm):
        return self.distance(p1, p2) * pixels_to_cm

    def reguler_check(self, dt):
        self.fig, self.ax1 = plt.subplots(1, 1, facecolor=('#EEEEEE'))
        self.ax1.set_facecolor('#EEEEEE')
        self.ax1.set_xlim(0, 640)
        self.ax1.set_ylim(0, 480)

        bg = mpimg.imread("asset/Image_Field.png")
        self.ax1.imshow(bg, extent=[0, 640, 0, 480])

        points = np.zeros(1)
        point = 0

        ret, img = self.cap.read()

        if not ret:
            print("Error: Unable to capture frame")

        arucoFound = self.findArucoMarkers(img)
        # Loop semua marker augmented satu per satu
        if len(arucoFound[0]) != 0:
            for bbox, ids in zip(arucoFound[0], arucoFound[1]):
                id = ids[0]
                if id in self.augDic.keys():
                    img = self.augmentAruco(bbox, id, img, self.augDic[id], drawId=False)

                    # Hitung kecepatan pergerakan marker
                    center = np.mean(bbox[0], axis=0)
                    if id in self.prev_frames:
                        distance_moved = self.distance(center, self.prev_frames[id])

                        # Hitung waktu yang diperlukan untuk perubahan tersebut
                        time_elapsed = time.time() - self.prev_times[id]

                        # Hitung kecepatan (jarak_perubahan / waktu_perubahan)
                        velocity = self.distance_cm(center, self.prev_frames[id], self.pixels_to_cm) / time_elapsed

                        x_start = int(bbox[0][0][0])
                        y_start = int(bbox[0][0][1])
                        angle = 45 + math.atan2(y_start - center[1], center[0] - x_start ) * ( 180 / np.pi )

                        #assume that all robot id is <= 21
                        if(id <= 25):
                            self.ids.id_robot.text = f'{id}'
                            self.ids.position_robot.text = f'X:{center[0]:.2f}, Y:{center[1]:.2f}'
                            self.ids.velocity_robot.text = f'{velocity:.2f}'
                            self.ids.angle_robot.text = f'{angle:.2f}'
                            logo = mpimg.imread("asset/Logo_Robot.png")
                            
                        else:                        
                            logo = mpimg.imread("asset/Logo_Object.png")

                            print(SETPOINT_COORD)
                            print((SETPOINT_COORD[0][0] - TOLERANCE))
                            print(center[0])

                            if(center[0] >= (SETPOINT_COORD[0][0] - TOLERANCE) and center[0] <= (SETPOINT_COORD[0][0] + TOLERANCE)):
                                if(center[1] >= (SETPOINT_COORD[0][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[0][1] + TOLERANCE)):
                                    point = 100

                                elif(center[1] >= (SETPOINT_COORD[1][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[1][1] + TOLERANCE)):
                                    point = 50        
                            
                                elif(center[1] >= (SETPOINT_COORD[2][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[2][1] + TOLERANCE)):
                                    point = 50 
                                
                                else:
                                    point = 0

                            elif(center[0] >= (SETPOINT_COORD[3][0] - TOLERANCE) and center[0] <= (SETPOINT_COORD[3][0] + TOLERANCE)):
                                if(center[1] >= (SETPOINT_COORD[3][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[3][1] + TOLERANCE)):
                                    point = 50

                                elif(center[1] >= (SETPOINT_COORD[4][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[4][1] + TOLERANCE)):
                                    point = 50        

                                else:
                                    point = 0

                            elif(center[0] >= (SETPOINT_COORD[5][0] - TOLERANCE) and center[0] <= (SETPOINT_COORD[5][0] + TOLERANCE)):
                                if(center[1] >= (SETPOINT_COORD[5][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[5][1] + TOLERANCE)):
                                    point = 50

                                elif(center[1] >= (SETPOINT_COORD[6][1] - TOLERANCE) and center[1] <= (SETPOINT_COORD[6][1] + TOLERANCE)):
                                    point = 50           

                                else:
                                    point = 0
                            else:
                                point = 0
                        
                        rot_logo = imutils.rotate(logo, angle=angle) 
                        tx, ty = center
                        self.ax1.imshow(rot_logo, extent=(tx - 15, tx + 15, 480 - ty - 15, 480 - ty + 15))

                    self.frames[id] = center
                    self.prev_frames[id] = center
                    self.prev_times[id] = time.time()
                    np.append(points, point)
                    
                    print(point)

        total_point = np.sum(points)

        self.ids.aruco_detected.text = f'{self.frames}'
        self.ids.value_point.text = f'{total_point}'

        if(total_point > 0):
            self.ids.value_point.md_bg_color = (.0, .6, .0, 1)
        else:
            self.ids.value_point.md_bg_color = (.6, .0, .0, 1)        

        self.ax1.tick_params(left = False, right = False , labelleft = False, labelbottom = False, bottom = False)
        # self.ax2.tick_params(left = False, right = False , labelleft = False, labelbottom = False, bottom = False)
        self.ids.layout_image.clear_widgets()
        self.ids.layout_image.add_widget(FigureCanvasKivyAgg(self.fig))

class DigitalTwinMobileRobotApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "BlueGray"
        self.icon = 'asset/Icon_Logo.png'
        # Window.fullscreen = 'auto'
        # Window.borderless = True
        Window.size = 1920, 1080
        # Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')
        return screen


if __name__ == '__main__':
    DigitalTwinMobileRobotApp().run()