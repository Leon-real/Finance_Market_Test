import pandas as pd
import time
import psutil
import matplotlib.pyplot as plt

plt.rcParams['animation.html'] = 'jshtml'

fig = plt.figure(figsize=(10,5))
ax = fig.add_subplot(111)

i=0
x=[]
y=[]
fig.show()

while True:
    print("hi")
    x.append(i)
    y.append(psutil.cpu_percent())

    ax.plot(x,y,color='b')
    fig.canvas.draw()
    plt.pause(0.1)
    time.sleep(0.1)
    i+=1