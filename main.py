import numpy as np
import time
import cv2
import cv2.aruco as aruco
from PIL import Image, ImageDraw
import os
from kivymd.app import MDApp
from kivymd.toast import toast
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt

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

    def delayed_init(self, dt):
        self.cap = cv2.VideoCapture(0)
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

    def reguler_check(self, dt):
        ret, img = self.cap.read()
        img_bg = plt.imread("asset/Image_Field.png")
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

        # img_bg = Image.open("asset/Image_Field.png").convert("RGBA")
        # mask = Image.new("L", img_bg.size, 0)
        # draw = ImageDraw.Draw(mask)
        # draw.ellipse((300, 1500, 1220, 2250), fill=185)
        # # x,y = img.size
        # # img2 = Image.open("/home/crow.jpg").convert("RGBA").resize((x,y))

        # img_new = Image.composite(img, img_bg, mask=mask)

        self.ax.imshow(img)
        # self.ax.imshow(img_new)
        self.ax.tick_params(left = False, right = False , labelleft = False, labelbottom = False, bottom = False) 

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
        Window.borderless = True
        # Window.size = 1080, 640
        # Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')
        return screen


if __name__ == '__main__':
    DigitalTwinMobileRobotApp().run()