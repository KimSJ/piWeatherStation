#! /usr/bin/python

from json import loads
from urllib2 import urlopen
from time import sleep, time
from datetime import datetime
import serial
import random
try:
    from myurl import myURL
except:
    print "localisation data not found. You need to create myurl.py starting from the myurl.sample.py example"
    exit()

#convert string to hex
def toHex(s):
    if len(s)==0:
        return "Null"

    lst = []
    for ch in s:
        hv = hex(ord(ch)).replace('0x', '')
        if len(hv) == 1:
            hv = '0'+hv
        lst.append(hv)
    
    return reduce(lambda x,y:x+y, lst)

# print out as a percentage
def doPercent(i):
    return str(int(round(i*100)))

###### Main program #########
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
except serial.SerialException:
    try:
        ser = serial.Serial('/dev/serial0', 115200, timeout=1)
    except serial.SerialException:
        try:
            ser = serial.Serial('COM8', 115200, timeout=1)
        except serial.SerialException:
                print("Serial port not found")
                exit()

# set up sleep and wake settings...
ser.write('thsp=30\xFF\xFF\xFF')   
ser.write('thup=1\xFF\xFF\xFF')   


while True:
    try:
        forecastFile = urlopen(myURL)

        ser.write('t0.txt="hrs"\xFF\xFF\xFF')

        forecastRaw = forecastFile.read()
        forecastFile.close()

        forecast = loads(forecastRaw)

        print "Current probability: "+doPercent(forecast['currently']['precipProbability']*100)+"%"

        timeNow = forecast['currently']['time']

        print "summary: "+forecast['hourly']['summary']
        #print forecast['hourly']['summary'].encode('ascii','ignore')
        ser.write('g0.txt="Summary: '+forecast['hourly']['summary'].encode('ascii','ignore')+'"\xFF\xFF\xFF')

        hourly = forecast['hourly']['data']

        rainExpected = -1
        for hour in hourly:
            offsetHours = (hour['time']-timeNow)/3600
            if (hour['precipProbability'] > 0.1):
                #continue
                rainExpected = offsetHours
                break
            # print str(offsetHours)+": "+doPercent(hour['precipProbability'])

        if (rainExpected>0):
            print "Rain expected in "+str(rainExpected)+ " hours"
            ser.write('t1.txt="'+str(rainExpected)+'"\xFF\xFF\xFF')
            ser.write('t2.txt="until rain likely"\xFF\xFF\xFF')   
        else:
            ser.write('t1.txt=">48"\xFF\xFF\xFF')
            ser.write('t2.txt="no rain is likely"\xFF\xFF\xFF')
            print "No rain expected in next "+str(offsetHours+1)+" hours"

        # Now populate the graph
        graphData=[]
        for hour in hourly:
            graphData.insert(0,[hour['precipProbability'],hour['time']])

        ser.write('cle 4,255'+'\xFF\xFF\xFF') # clear graph display

        # graph channel 0 - green
        # graph channel 1 - orange
        # graph channel 2 - red
        # graph channel 3 - black (used for ticks)
        # higer channels overwrite lower ones

            

        for d in graphData:
            v=d[0]
            t=datetime.fromtimestamp(d[1]).strftime('%H') # extract just the hours

            # write the ticks, with bigger ones for midday and midnight

            for j in range(5):
                ser.write('add 4,3,0'+'\xFF\xFF\xFF')

            if t == "00":
                ser.write('add 4,3,18'+'\xFF\xFF\xFF')
            elif t == "12":
                ser.write('add 4,3,8'+'\xFF\xFF\xFF')
            else:
                ser.write('add 4,3,3'+'\xFF\xFF\xFF')


            #v=random.random() # generate test data
            for i in range(3):
                ser.write('add 4,0,'+str(v*50)+'\xFF\xFF\xFF') # green

                if v > 0.2:
                    ser.write('add 4,1,'+str(v*50)+'\xFF\xFF\xFF') # orange
                else:
                    ser.write('add 4,1,0'+'\xFF\xFF\xFF')

                if v > 0.4:
                    ser.write('add 4,2,'+str(v*50)+'\xFF\xFF\xFF') # red
                else:
                    ser.write('add 4,2,0'+'\xFF\xFF\xFF')

                ser.write('add 4,0,0'+'\xFF\xFF\xFF')
                ser.write('add 4,1,0'+'\xFF\xFF\xFF')
                ser.write('add 4,2,0'+'\xFF\xFF\xFF')

        sleep(300)

    except IOError:
        print("website not found")
        ser.write('cle 4,255'+'\xFF\xFF\xFF') # clear graph display
        ser.write('t0.txt=""\xFF\xFF\xFF')
        ser.write('t1.txt=""\xFF\xFF\xFF')
        ser.write('g0.txt=""\xFF\xFF\xFF')
        ser.write('t2.txt="forecast unavailable"\xFF\xFF\xFF')
        sleep(5)
    except KeyError:
        print("weather data bad format")
        ser.write('cle 4,255'+'\xFF\xFF\xFF') # clear graph display
        ser.write('t0.txt=""\xFF\xFF\xFF')
        ser.write('t1.txt=""\xFF\xFF\xFF')
        ser.write('g0.txt=""\xFF\xFF\xFF')
        ser.write('t2.txt="weather data error"\xFF\xFF\xFF')
        sleep(300) # try again in five minuits

