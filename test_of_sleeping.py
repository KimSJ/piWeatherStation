# test of sleeping

from json import loads
from urllib2 import urlopen
from time import sleep, time
from datetime import datetime
import serial
import random

# def to_hex_string(s):
#     if len(s)==0:
#         return ""
#     h=[]
#     for ch in s:
#         h=h+[hex(ord(ch))]
#     return " ".join(h)

# define a custom error for failed response read
class ResponseError(IOError):
    pass

def get_response(raiseError=False):
    s=""
    count=0
    while True:
        c=ser.read()
        s+=c
        if c=="\xFF":
            count+=1
        else:
            count=0
        if count==3:
            return s
        if not c:
            if raiseError:
                raise ResponseError("Serial input timeout without complete response. Input received: '"+s+"'")
                print "nothing more to read"
            else:
                return s

def do_update():
    print "Do update"
    return

###### Main program #########
print "\nKimbeau Acme Forecaster v1.0.0"
print "##############################\n"


try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)
    print "Using /dev/ttyUSB0"
except serial.SerialException:
    try:
        ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)
        print "Using /dev/serial0"
    except serial.SerialException:
        try:
            ser = serial.Serial('COM8', 115200, timeout=0.1)
            print "Using COM8"
        except serial.SerialException:
                print("Serial port not found")
                exit()
ser.timeout=0.1

# set up sleep and wake settings...

ser.write('sendxy=1\xFF\xFF\xFF') # turn on sending touch events

count=0
ser.write('dim=100\xFF\xFF\xFF')
do_update()
next_update_time = time() + (5*60) # refresh every five minutes
while True:
    r = get_response()
    if r:
        ser.write('dim=100\xFF\xFF\xFF')
        count = 0
        # if r[0] == '\x67':
        #     on = "on" if ord(r[5]) else "off" # r[5] is 1 for touch on, 0 for touch off
        #     print "touch %(on)s at x:%(x)i, y:%(y)i"%{"on":on, "x":ord(r[2])+ord(r[1])*265, "y":ord(r[4])+ord(r[3])*265}
        # else:
        #     print to_hex_string(r)
    else:
        count +=1 # counting (roughly) tenths of second -- serial timeout is 1/10th second
    if count >= 300:
        count = 300
        ser.write('dim=0\xFF\xFF\xFF')
    elif count >= 200:
        ser.write('dim=dim-1\xFF\xFF\xFF')

    # now do data update if needed
    if time() > next_update_time:
        do_update()
        next_update_time = time() + 300
