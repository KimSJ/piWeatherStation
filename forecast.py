#! /usr/bin/python

from json import loads
from urllib2 import urlopen
from time import sleep, time
from datetime import datetime
import serial
import random

# intitalise logging
import logging
logging.basicConfig(filename='/home/pi/piWeatherStation/forecast.log', filemode = 'w', level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("forecast.py started")

try:
    from myurl import myURL
except:
    e = ("localisation data not found. You need to create myurl.py"
       + " starting from the myurl.sample.py example")
    logger.error(e)
    print(e)
    exit()

logger.info("URL configured")
logger.debug("URL="+myURL)

def to_hex_string(s):
    if len(s)==0:
        return ""
    h=[]
    for ch in s:
        h=h+[hex(ord(ch))]
    return " ".join(h)

# print out as a percentage
def doPercent(i):
    return str(int(round(i*100)))

# define a custom error for failed response read
class ResponseError(IOError):
    pass

def get_response():
    # get a response string from the Nextion, if any pending
    # relies on serial timeout setting to manage null and error cases
    # a timeout with no characters received is a perfectly normal case
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
            logger.debug("Nextion response received: " + to_hex_string(s))
            return s # the normal exit for received responses
        if not c: # we have a serial input timeout with no or an incomplete response
            if s: # this is the incomplete case, which we don't expect
                logger.warning("Nextion incomplete response received: " + to_hex_string(s))
            return s # return both null string and incomplete ones.

def do_screen_reset():
    # ensure that screen is properly reset
    resetNotDone=True
    while resetNotDone:
        resetTimeout=time()+2
        logger.debug("Sending screen reset")
        ser.reset_input_buffer()
        ser.write('rest\xFF\xFF\xFF') # set default (reset) state...

        # pause needed before reset is complete
        logger.debug("waiting for reset response")
        while time()<resetTimeout:
            # start by waiting for string of \xFFs to ensure sync'd
            c=""
            while c != '\xFF' and time()<resetTimeout:
                c=ser.read() # wait for an FF
                logger.debug("c: " + to_hex_string(c))
            if time()>=resetTimeout:
                break
            c=ser.read()
            while c == "" and time()<resetTimeout: # wait for a char
                c=ser.read()
            if time()>=resetTimeout:
                break
            while c=='\xFF' and time()<resetTimeout: # swallow extra FFs
                c=ser.read()
                logger.debug("c: " + to_hex_string(c))
            if time()>=resetTimeout:
                break

            logger.debug("looking for sync, got: "+ to_hex_string(c))
            if c != '\x88':
                continue # not the response we're hoping for -> look for sync again
            #finally, look for the end of the reset confirmation
            s=""
            while s != '\xFF\xFF\xFF' and time()<resetTimeout:
                s = s[-2:]+ser.read() # add a new character on the end
                logger.debug("final sync search: "+to_hex_string(s))
            # we arrive here either timed-out or success
            # so, if we've timed out, we need to do the whole thing again
            if time()>=resetTimeout:
                logger.debug("Failed reset, retrying")
                break
            else:
                logger.info("Successful reset")
                return # yes! we got it OK



################################
######### Main program #########
################################

print "\nKimbeau Acme Forecaster v1.1.1"
print "##############################\n"


try:
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    logger.info("Using /dev/ttyUSB0")
    print "Using /dev/ttyUSB0"
except serial.SerialException:
    try:
        ser = serial.Serial('/dev/serial0', 115200)
        logger.info("Using /dev/serial0")
        print "Using /dev/serial0"
    except serial.SerialException:
        try:
            ser = serial.Serial('COM8', 115200)
            logger.info("Using COM8")
            print "Using COM8"
        except serial.SerialException:
                logger.error("Serial ort not found")
                print("Serial port not found")
                exit()
ser.timeout=0.1

do_screen_reset()
ser.write('sendxy=1\xFF\xFF\xFF') # turn on sending touch events

idle_count=0 # counting roughly tenths of seconds until screen dim
             # (thanks to serial timeout setting being 0.1 secs)
             # starts with screen on, of course


while True:
    try:
        forecastFile = urlopen(myURL)
        forecastRaw = forecastFile.read()
        forecastFile.close()

        forecast = loads(forecastRaw)

        print("Current probability: "
            + doPercent(forecast['currently']['precipProbability']*100)
            + "%"
            )


        print "summary: "+forecast['hourly']['summary']
        print("humidity: "
            + doPercent(forecast['currently']['humidity'])
            + "%")
        #print forecast['hourly']['summary'].encode('ascii','ignore')
        ser.write('g0.txt="Summary: '
              + forecast['hourly']['summary'].encode('ascii','ignore')
              + " Current humidity: "
              + doPercent(forecast['currently']['humidity'])
              + "%" + '"\xFF\xFF\xFF')

        hourly = forecast['hourly']['data']
        timeNow = hourly[0]['time']

        rainExpected = -1
        for hour in hourly:
            offsetHours = (hour['time']-timeNow)/3600
            if (hour['precipProbability'] > 0.1):
                #continue
                rainExpected = offsetHours
                break

        ser.write('t0.txt="hrs"\xFF\xFF\xFF')
        if (rainExpected > -1):
            print "Rain expected in "+str(rainExpected)+ " hours"
            ser.write('t1.txt="'+str(rainExpected)+'"\xFF\xFF\xFF')
            if (rainExpected > 0):
                ser.write('t2.txt="until rain likely"\xFF\xFF\xFF')
            else:
                ser.write('t2.txt="rain likely now"\xFF\xFF\xFF')
            if (rainExpected < 2):
                ser.write('t0.txt="hr"\xFF\xFF\xFF')
        else:
            ser.write('t1.txt=">48"\xFF\xFF\xFF')
            ser.write('t2.txt="no rain is likely"\xFF\xFF\xFF')
            print "No rain expected in next "+str(offsetHours+1)+" hours"


        ################# Now populate the graph ###################
        # data writen rightmost-point first, so has to be reversed
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
            t=datetime.fromtimestamp(d[1]).hour # extract just the hours

            # write the ticks, with bigger ones for midday and midnight
            # each hour is six data points
            for j in range(5):
                ser.write('add 4,3,0'+'\xFF\xFF\xFF')

            if t == 0:
                ser.write('add 4,3,18'+'\xFF\xFF\xFF')
            elif t == 12:
                ser.write('add 4,3,8'+'\xFF\xFF\xFF')
            else:
                ser.write('add 4,3,3'+'\xFF\xFF\xFF')

            # write the data, in three colours, depending on probability
            # to make it solid, alternate points are written at zero
            for i in range(3):
                ser.write('add 4,0,'+str(v*50)+'\xFF\xFF\xFF') # green for low probablility

                if v > 0.2:
                    ser.write('add 4,1,'+str(v*50)+'\xFF\xFF\xFF') # overwrite with orange
                else:
                    ser.write('add 4,1,0'+'\xFF\xFF\xFF')

                if v > 0.4:
                    ser.write('add 4,2,'+str(v*50)+'\xFF\xFF\xFF') # overwrite with red
                else:
                    ser.write('add 4,2,0'+'\xFF\xFF\xFF')

                ser.write('add 4,0,0'+'\xFF\xFF\xFF')
                ser.write('add 4,1,0'+'\xFF\xFF\xFF')
                ser.write('add 4,2,0'+'\xFF\xFF\xFF')

        # manage the screen brightness until it's time for the next update
        next_update_time = time() + (5*60) # refresh every five minutes
        while time() < next_update_time:
            r = get_response()
            if r:
                ser.write('dim=100\xFF\xFF\xFF')
                idle_count = 0
            else:
                idle_count +=1 # counting (roughly) tenths of second -- serial timeout is 1/10th second
            if idle_count >= 300:
                idle_count = 300
                ser.write('dim=0\xFF\xFF\xFF')
            elif idle_count >= 200:
                ser.write('dim=dim-1\xFF\xFF\xFF')

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
        sleep(300) # try again in five minutes

