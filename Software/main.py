# 1: hold bootselect button while pluggin in. Drop the uf2 file into the disk.
# 2: right click on the files to upload to the detector.
# I've added the libraries to the lib folder. Right click on it, then upload it to the pico.
# Run-> Configure Interpreter -> select MicroPython RPPico

import machine
import utime
import math
import time
import os
import framebuf
import _thread

import uos
import sdcard

from ssd1306 import SSD1306_I2C

from machine import Pin, I2C, ADC, Timer, PWM
from bmp280 import *
from functions import *

coincidence_event_rate = 0
coincidence_event_rate_std = 0
event_rate = 0
event_rate_std = 0

class detectorClass():
    def __init__(self):
        self.trigger_mode     = 'running' # interupt or running
        self.SignalThreshold  = 200 #[0 - 4095 on HGain]
        self.OLED             = True   # Turn on/off OLED.
        self.Buzzer           = False   # Turn on/off OLED.
        self.VERBOSE          = True   #print out detector information through the serial port.
        
        self.OLED_SDA         = 14
        self.OLED_SCL         = 15
        self.COINCIDENCE      = False  #Is there another detector plugged into the RJ45 connector?
        self.SignalPin1       = 26
        self.SignalPin2       = 28
        self.LEDPin1     	  = 9
        self.PicoLED     	  = 25
        self.LEDPin2          = 8
        self.LEDBrightness    = 100  # Percent of full brightness
        self.CoincidencePin1  = 0
        self.CoincidencePin2  = 1
        self.ResetPin		  = 23
        self.TriggerReadout   = False
        self.BuzzerPin        = 6
        self.DetectorName     = 'CW'
        self.TotalDeadtime    = 0
        self.SD_CS			  = 13
        self.SD_TX            = 11
        self.SD_RX			  = 12
        self.SD_SCK 		  = 10
        self.SD_Detect 		  = 22
        self.Trigger		  = 19
        self.roll_over_times = []

class eventClass():
    def __init__(self):
        self.EventNumber         = 0
        self.CoincidentEventNumber = 0
        self.ADC_value           = 0
        self.SiPM_pulse_amplitdue = 0
        self.Timestamp           = 0   
        self.Pressure            = 0
        self.Temperature         = 0
        self.Deadtime            = 0
        self.Coincident			 = 0

d = detectorClass()
e = eventClass()

setup_BMP280Sensor(d,e)

scan_I2CDevices(d)
setup_detector_name(d)
setup_signal_treshold(d)
setup_OLED(d)
setup_GPIO(d)
OLEDSlashScreen(d)
check_CoincidentDetector(d,e)
setup_ADC(d)
setup_buzzer(d)

setup_microSD(d, fileprefix = 'CW')
#calculate_baseline_voltages(d)
write_microSD_header(d)
print_serial_header(d)


timer = Timer(period=500, mode=Timer.PERIODIC, callback = lambda t:UpdateOLED(d,e))

def event_Trigger(pin):
    trigger_Detector(d,e)
    
d.start_time = millis()

if d.trigger_mode == 'interupt':
    d.Trigger.irq(trigger=d.Trigger.IRQ_RISING, handler=event_Trigger)
    while True:
        continue

elif (d.trigger_mode == 'running'):
    while True:
        e.ADC_value_2 = d.ADC2.read_u16()
        if (e.ADC_value_2  > d.TriggerThreshold):
            trigger_Detector(d,e)
            
         
       