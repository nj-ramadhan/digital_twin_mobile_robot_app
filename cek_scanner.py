import serial

ser = serial.Serial(baudrate=115200, port='COM3')

while True :
    data = str(ser.read_until(b'\r'),'UTF-8')

    # print(str(data, 'UTF-8'))
    print(data)