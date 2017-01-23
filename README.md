# piWeatherStation
Use a Nextion display with a Raspberry Pi to display time to next rain, with data from api.darksky.net/forecast

My use case is to tell me quickly how long I've got before I'm likely to need to bring the washing in.

## Hardware

The display I used was the small (2.8") basic display. You need to upload the image to the display. The Nextion software needed to do this only works on Windows, and needs a USB->5V serial adaptor. You'll find the required image (`Weather.HMI`) in the Nextion subdirectory of this repository.

As you'll see from the source code, I developed in a number of different configurations. The python code runs happily in Ubuntu, Windows or Raspbian. Using the USB serial adaptor, that appears as COM8 or /dev/ttyUSB0 on my dual-boot laptop, and as /dev/ttyUSB0 on Raspbian. Developing on the laptop is easier to start with (expecially when messing with the screen layout), and it can be tested using the USB on the Pi, but in the final version you'll want to connect direct to the Pi's serial port:

* pin 4: 5V
* pin 6: GND
* pin 8: (TxD on the Pi) -> RxD on the Nextion
* pin 10: (RxD on the Pi) <- TxD on the Nextion

You can connect the Nextion connector leads directly to the Pi's header.

## Pi software configuration
The system runs Raspbian Lite, headless. Start with a standard install, and make the following changes:

### Networking
Obviously, to read weather data the pi needs to be connected to the internet. Up to you how to do that, but it's probably your first step. I happen to have a Homeplug wifi extender in my kitchen where I've installed the weather watcher, and that has two wired Ethernet outputs, so I've connected the forecaster to that.

The way I develop is to connect using ssh; alternatively you can use screen and keyboard on the pi.

To enable SSH on the pi, you can either start with a keyboard and monitor, and use raspi-config to change the "Interfacing options" SSH setting, or if you can't get to that, using another system which can read the SD card you can add a file called `ssh` to `/boot` (a zero-length file is fine). The /boot directory is mounted from the partition you can see from Windows, so you should be able to do that even on a Windows machine.

### Serial
By default, Raspbian is configured to use the on-board serial port as a log-in terminal. The easiest way to do this is to use `raspi-config` to turn the port OFF, (which will totally disable it), then turn it on again by adding/editing a line

      enable_uart=1

in /boot/config.txt

There is also a modem manager process which wanders round at startup sending "hello" to every serial terminal (in the vague hope it will find something responding, presumably). You can disable this by issuing at the command line

      systemctl disable ModemManager.service

### system upgrade
    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install git python-pip
    sudo pip install pyserial

### Install this program
assuming you've logged in as user "pi", from the home direcctory run

    git clone https://github.com/KimSJ/piWeatherStation.git
    cd piWeatherStation
    cp myurl.sample.py myurl.py
    nano myurl.py
    
and add the information about your own key and your particular location.

### Turn off video
Since the device works headless, you can save a little power by totally disabling the video. I added

      @reboot /opt/vc/bin/tvservice -o

to the system crontab (edit it using `sudo crontab -e`)

### Auto-start the forecaster on boot
Add the following line to the system crontab (`sudo crontab -e`)

    @reboot /bin/sleep 20 && /usr/bin/python /home/pi/piWeatherStation/forecast.py

Now just reboot and you should be good to go. I've not worked out why the pause is needed, but bad things happen if it's not there. :-(

# Useful links

[Nextion_Instruction_Set](https://www.itead.cc/wiki/Nextion_Instruction_Set)

[Element 14 info page](https://www.element14.com/community/community/arduino/blog/2016/02/22/nextion-hmi-display-a-user-interface-that-is-simple-and-easy-to-use)

[Nextion product information](https://www.itead.cc/wiki/Nextion_HMI_Solution)
