import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import animation
import numpy as np

x = [0, 1, 2]
y = [0, 1, 2]
yaw = [0.0, 0.5, 1.3]
fig = plt.figure()

imageList = ["asset/Logo_ITB.png", "asset/Logo_POLMAN.png", "asset/Logo_KRTMI.png"]
coordinatesList = [[0, 0], [150, 200], [250, 200]]

ax = fig.add_subplot(111)
ax.set_xlim(0, 300)
ax.set_ylim(0, 300)

bg = plt.imread("asset/Image_Field.png")
im = ax.imshow(bg, extent=[0, 300, 0, 300])

imgplot = [None] * len(imageList)
for i in range(3):
    imageFile = imageList[i]
    img=mpimg.imread(imageFile)
    tx, ty = coordinatesList[i]
    ax.imshow(img, extent=(tx, tx + 30, ty, ty + 30))

ax.tick_params(left = False, right = False , labelleft = False, labelbottom = False, bottom = False) 

# def init():
#     ax.add_patch(img)
#     return img,

# def animate(i):
#     img.set_xy([x[i], y[i]])
#     img.angle = -np.rad2deg(yaw[i])
#     return img,

# anim = animation.FuncAnimation(fig, animate,
#                                init_func=init,
#                                frames=len(x),
#                                interval=500,
#                                blit=True)

plt.show()