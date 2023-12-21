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
        self.coordinatesList = [[0, 0], 
                           [200, 200], 
                           [120, 250]]
        self.coordinatesList_prev = self.coordinatesList

    def delayed_init(self, dt):
        self.cap = cv2.VideoCapture(1)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,320)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,240)
        # cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        # cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        # self.cap.set(cv2.CAP_PROP_FPS, 30)
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        if not self.cap.isOpened():
            print("Error: Unable to access the camera")
            return

        self.augDic = self.loadImages("markers")
        self.prev_frames = {}
        self.prev_times = {}
        self.pixels_to_cm = 0.1 # Sesuaikan dengan informasi fisik dari ArUco marker atau objek yang digunakan
        # self.update_interval = 0.5  # Interval pembacaan kecepatan (dalam detik)

        self.fig = plt.figure()
        self.fig.tight_layout()
        self.ax = self.fig.add_subplot(111)
        self.ax.tick_params(left = False, right = False , labelleft = False, labelbottom = False, bottom = False) 
        self.ids.layout_image.add_widget(FigureCanvasKivyAgg(self.fig))    

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

    def angle_calculate(self, pt1, pt2, trigger = 0):  # function which returns angle between two points in the range of 0-359
        angle_list_1 = list(range(359,0,-1))
        #angle_list_1 = angle_list_1[90:] + angle_list_1[:90]
        angle_list_2 = list(range(359,0,-1))
        angle_list_2 = angle_list_2[-90:] + angle_list_2[:-90]
        x=pt2[0]-pt1[0] # unpacking tuple
        y=pt2[1]-pt1[1]
        angle=int(math.degrees(math.atan2(y,x))) #takes 2 points nad give angle with respect to horizontal axis in range(-180,180)
        if trigger == 0:
            angle = angle_list_2[angle]
        else:
            angle = angle_list_1[angle]
        return int(angle)

    def reguler_check(self, dt):
        pos = np.array([2, 1])
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

                        print(f'bbox:{bbox}')
                        print(f'angle:{angle}')

                        # angle = self.angle_calculate(x_start, y_start)

                        # print("id: ",id,"center:",center)
                        self.ids.id_robot.text = f'{id}'
                        self.ids.position_robot.text = f'X:{center[0]:.2f}, Y:{center[1]:.2f}'
                        self.ids.velocity_robot.text = f'{velocity:.2f}'
                        self.ids.angle_robot.text = f'{angle:.2f}'

                        # Ambil ukuran teks kecepatan
                        (text_width, text_height), _ = cv2.getTextSize(f"V: {velocity:.2f} cm/s", cv2.FONT_HERSHEY_PLAIN, 1.5, 2)

                        # Atur posisi teks ID sedikit lebih tinggi agar tidak terhalang
                        y_text = y_start - text_height - 15

                        # Tampilkan teks ID dan kecepatan pada frame
                        cv2.putText(img, f"ID: {id}", (x_start, y_text), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
                        cv2.putText(img, f"V: {velocity:.2f} cm/s", (x_start, y_text + 20), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 2)

                        # img_new = Image.composite(img, img_bg, mask=bbox)

                    # Simpan frame dan waktu sebelumnya untuk perhitungan selanjutnya
                    self.prev_frames[id] = center
                    self.prev_times[id] = time.time()

        # # img_bg = Image.open("asset/Image_Field.png").convert("RGBA")
        # # mask = Image.new("L", img_bg.size, 0)
        # # draw = ImageDraw.Draw(mask)
        # # draw.ellipse((300, 1500, 1220, 2250), fill=185)
        # # # x,y = img.size
        # # # img2 = Image.open("/home/crow.jpg").convert("RGBA").resize((x,y))

        # # img_new = Image.composite(img, img_bg, mask=mask)

        # self.ax.imshow(img)
        # # self.ax.imshow(img_new)

        # imageList = ["asset/Logo_ITB.png", "asset/Logo_POLMAN.png", "asset/Logo_KRTMI.png"]
        
        # randMovementCoordinates = [[np.random.randint(-10,10), np.random.randint(-10,10)], 
        #                    [np.random.randint(-10,10), np.random.randint(-10,10)], 
        #                    [np.random.randint(-10,10), np.random.randint(-10,10)]]
        # self.coordinatesList = np.add(self.coordinatesList_prev, randMovementCoordinates)
        # print(self.coordinatesList)

        # self.fig = plt.figure()
        # self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, facecolor=('#EEEEEE'))
        self.fig, self.ax1 = plt.subplots(1, 1, facecolor=('#EEEEEE'))
        # self.ax1 = self.fig.add_subplot(121, facecolor=('#EEEEEE'))
        self.ax1.set_facecolor('#EEEEEE')
        self.ax1.set_xlim(0, 640)
        self.ax1.set_ylim(0, 480)
        # self.ax1.set_aspect('box')
        # self.ax1.set_box_aspect(aspect=(1, 1))

        bg = mpimg.imread("asset/Image_Field.png")
        self.ax1.imshow(bg, extent=[0, 640, 0, 480])

        # imgplot = [None] * len(imageList)
        # for i in range(3):
        #     imageFile = imageList[i]
        #     img=mpimg.imread(imageFile)
        #     tx, ty = self.coordinatesList[i]
        #     self.ax.imshow(img, extent=(tx, tx + 30, ty, ty + 30))
        try:
            self.coordinates = center            
            logo = mpimg.imread("asset/Logo_POLMAN.png")
            rot_logo = imutils.rotate(logo, angle=angle) 

            tx, ty = self.coordinates
            self.ax1.imshow(rot_logo, extent=(tx - 15, tx + 15, 480 - ty - 15, 480 - ty + 15))
            # self.ax2.imshow(img)
            # self.coordinatesList_prev = self.coordinatesList
            self.coordinates_prev = self.coordinates
        except:
            pass

        if(self.coordinates[0] >= 315 and self.coordinates[0] <= 325):
            if(self.coordinates[1] >= 235 and self.coordinates[1] <= 260):
                self.point = 100

            elif(self.coordinates[1] >= 395 and self.coordinates[1] <= 305):
                self.point = 50        
        
            elif(self.coordinates[1] >= 65 and self.coordinates[1] <= 75):
                self.point = 50 
            
            else:
                self.point = 0

        elif(self.coordinates[0] >= 175 and self.coordinates[0] <= 195):
            if(self.coordinates[1] >= 315 and self.coordinates[1] <= 325):
                self.point = 50

            elif(self.coordinates[1] >= 145 and self.coordinates[1] <= 165):
                self.point = 50        

            else:
                self.point = 0

        elif(self.coordinates[0] >= 465 and self.coordinates[0] <= 475):
            if(self.coordinates[1] >= 315 and self.coordinates[1] <= 325):
                self.point = 50

            elif(self.coordinates[1] >= 145 and self.coordinates[1] <= 165):
                self.point = 50           

            else:
                self.point = 0
        else:
            self.point = 0

        if(self.point > 0):
            self.ids.value_point.md_bg_color = (.0, .6, .0, 1)

        else:
            self.ids.value_point.md_bg_color = (.6, .0, .0, 1)

        self.ids.value_point.text = f'{self.point}'

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
        Window.fullscreen = 'auto'
        # Window.borderless = True
        # Window.size = 1920, 786
        # Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')
        return screen


if __name__ == '__main__':
    DigitalTwinMobileRobotApp().run()