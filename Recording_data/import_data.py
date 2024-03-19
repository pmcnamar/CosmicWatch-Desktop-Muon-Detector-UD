# This script requires one library:
# pyserial
# to install, type: >> pip install pyserial

from __future__ import print_function
import serial 
import time
import glob
import sys
import os
import os.path
import signal
from datetime import datetime
from multiprocessing import Process
import numpy as np
import math
import random
import platform
import pathlib 

print('Operating System: ',platform.system())

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    ComPort.close()     
    file.close() 
    sys.exit(0)

def serial_ports():
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
        sys.exit(0)
    result = []
    for port in ports:
        try: 
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

t1 = time.time()
port_list = serial_ports()
if (time.time()-t1)>2:
    print('Listing ports is taking unusually long. Try disabling your Bluetooth.')

print('\nWhich ports do you want to read from?')
for i in range(len(port_list)):
    print('  ['+str(i+1)+'] ' + str(port_list[i]))
print('  [h] help')

# Account for Python 2 and Python 3 syntax
if sys.version_info[:3] > (3,0):
    ArduinoPort = input("Select port: ")
    ArduinoPort = ArduinoPort.split(',')

elif sys.version_info[:3] > (2,5,2):
    ArduinoPort = raw_input("Select port(s): ")

nDetectors = len(ArduinoPort)
port_name_list = []

for i in range(len(ArduinoPort)):
	port_name_list.append(str(port_list[int(ArduinoPort[i])-1]))

if ArduinoPort == 'h':
    print_help1()
    sys.exit()


print('')

# Ask for file name:
cwd = os.getcwd()
default_fname = cwd+"/Data/CW_data.txt"
if sys.version_info[:3] > (3,0):
    fname = input("Enter file name (default: "+default_fname+")")
    if fname == '':
        path = pathlib.Path(default_fname)
        fname = default_fname
    pathlib.Path(path.parent).mkdir(parents=True, exist_ok=True)
elif sys.version_info[:3] > (2,5,2):
    fname = raw_input("Enter file name (default: "+default_fname+")")
    if fname == '':
        fname = default_fname
        if not os.path.exists(default_fname):
            os.makedirs(default_fname)
detector_name_list = []

#if fname == '':
print('  Saving data to: '+fname)

# Make a dictionary for each connected detector

for i in range(nDetectors):
    time.sleep(0.1)
    globals()['Det%s' % str(i)] = serial.Serial(str(port_name_list[i]),115200)
    time.sleep(0.1)
file = open(fname, "w")

# Get list of names, using 5 seconds of data.
print('')
print('Acquiring detector names')
det_names = []
t1 = time.time()
while (time.time()-t1) < 5:
    for i in range(nDetectors):
        if globals()['Det%s' % str(i)].inWaiting():
            data = globals()['Det%s' % str(i)].readline().decode().replace('\r\n','')    # Wait and read data 
            data = data.split("\t")
            det_names.append(data[-1])
            
#print("\nHere is a list of the detectors I see:")
det_names = list(set(det_names))
for i in range(len(det_names)):
    print("  "+str(i+1)+') '+det_names[i])

# Start recording data to file.
print("\nTaking data ...")
if platform.system() == "Windows":
    print("ctrl+break to termiante process")
else:
    print("Press ctl+c to terminate process")

while True:
    for i in range(nDetectors):
        if globals()['Det%s' % str(i)].inWaiting():
            data = globals()['Det%s' % str(i)].readline().decode().replace('\r\n','')    # Wait and read data 
            data = data.split("\t")
            ti = str(datetime.now()).split(" ")
            comp_time = ti[-1]
            data.append(comp_time)
            comp_date = ti[0].split('-')
            data.append(comp_date[2] + '/' +comp_date[1] + '/' + comp_date[0]) 
            for j in range(len(data)):
                file.write(data[j]+'\t')
            file.write("\n")
            print(*data, sep='\t')
            event_number = int(data[0])
            if event_number % 10 == 0: # Flush data to computer every 10 events
                file.flush() 

globals()['Det%s' % str(0)].close()     
file.close()  



