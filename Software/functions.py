import machine
import utime
import time
import os
import framebuf
import _thread
import uos
import sdcard
import math


from ssd1306 import SSD1306_I2C


from machine import Pin, I2C, ADC, Timer, PWM
from bmp280 import *



def sigmoid(SiPM_value):
    turn_over_value = 10
    sigmoid_width = 1.5
    return 1 / (1 + math.exp(-(SiPM_value-turn_over_value)/sigmoid_width))

def get_SiPM_peak_voltage(HGain_adc_value, LGain_adc_value):
    HGAIN_SiPM_peak_voltage = HGain_adc_value * (15/4095)
    LGAIN_SiPM_peak_voltage = LGain_adc_value * (985/4095)+15
    return '{:.1f}'.format(((1 - sigmoid(HGAIN_SiPM_peak_voltage))*HGAIN_SiPM_peak_voltage+ sigmoid(HGAIN_SiPM_peak_voltage)*LGAIN_SiPM_peak_voltage))
    
#def get_SiPM_peak_voltage(ADC_value):
#    calibration = 3
#    
#    return SiPM_peak_voltage
              
def write_to_microsd(d, e):
    if (d.is_SDAvailable == True):
        d.sd_file.write(str(e.EventNumber)+'\t'+str(e.Timestamp)+'\t'+str(e.ADC_value_1)+'\t'+str(e.ADC_value_2)+'\t'+str(e.SiPM_pulse_amplitdue)+'\t'+str(e.Pressure)+'\t'+str(e.Temperature)+'\t'+str(e.Deadtime)+'\t'+str(e.Coincident)+'\t'+d.DetectorName+'\n')
        if (e.EventNumber % 20) == 0:
            d.sd_file.flush()

def write_to_serial(d,e):
    print(str(e.EventNumber)+'\t'+str(e.Timestamp)+'\t'+str(e.ADC_value_1)+'\t'+str(e.ADC_value_2)+'\t'+str(e.SiPM_pulse_amplitdue)+'\t'+str(e.Pressure)+'\t'+str(e.Temperature)+'\t'+str(e.Deadtime)+'\t'+str(e.Coincident)+'\t'+d.DetectorName)

     
def UpdateOLED(d,e):
    td1 = micros()
    t1 = millis()
    d.bmp.force_measure()
    e.Pressure     = round(d.bmp.pressure,1)
    e.Temperature  = round(d.bmp.temperature,1)
        
    if (t1 - d.start_time) < 0.1:
        return

    if d.OLED:
        runtime = time_diff(t1, d.start_time)/1000.
        livetime  = runtime - (d.TotalDeadtime/1000.)
        coincidence_event_rate       = e.CoincidentEventNumber /livetime 
        coincidence_event_rate_std   = math.sqrt(e.CoincidentEventNumber) / livetime
        event_rate                   = e.EventNumber / livetime
        event_rate_std               = math.sqrt(e.EventNumber) / livetime
        
        hours                   = int(livetime / 3600.)
        minutes                 = int(livetime / 60.) % 60
        seconds                 = int(livetime) % 60
        
        
        livetime_readout = f'{hours:02d}'+":"+f'{minutes:02d}' +":"+f'{seconds:02d}' 
        d.display.fill(0)    
        x_offset = 0
        y_offset = 10
        
        if d.COINCIDENCE:
            d.display.text(d.DetectorName.upper(),int((128-(len(d.DetectorName) * 8))/2),5)
            d.display.text(livetime_readout,int((128- (len(livetime_readout) * 8))/2),15)
            
            count_readout= "TOTAL: "
            n_spaces = int(128-len(count_readout)*8-len(str(e.EventNumber))*8)/8
            for i in range(n_spaces):
                count_readout=count_readout+" "
            count_readout +=  str(e.EventNumber)

            d.display.text(count_readout,0,25)
            
            rate_readout = "%.3f" % event_rate +"+/-" + "%.3f" % event_rate_std +" Hz"
            if event_rate>= 10.:
                rate_readout = "%.2f" % event_rate +"+/-" + "%.2f" % event_rate_std +" Hz"
                
            d.display.text(rate_readout,int((128- (len(rate_readout) * 8))/2),35)
            
            count_readout= "COINC: "
            n_spaces = int(128-len(count_readout)*8-len(str(e.CoincidentEventNumber))*8)/8
            for i in range(n_spaces):
                count_readout = count_readout+" "
            count_readout +=  str(e.CoincidentEventNumber)
            d.display.text(count_readout,0,45)
            
            coincidence_rate_readout = "%.3f" % coincidence_event_rate +"+/-" + "%.3f" % coincidence_event_rate_std +" Hz"
            
            d.display.text(coincidence_rate_readout,int((128- (len(coincidence_rate_readout) * 8 ))/2),55)
            
            
        else:
            d.display.text(d.DetectorName.upper(),int((128-(len(d.DetectorName) * 8))/2),10)
            d.display.text(livetime_readout,int((128- (len(livetime_readout) * 8))/2),20)   
            
            count_readout= "Total: "
            n_spaces = int(128-len(count_readout)*8-len(str(e.EventNumber))*8)/8
            for i in range(n_spaces):
                count_readout=count_readout+" "
            count_readout +=  str(e.EventNumber)

            d.display.text(count_readout,0,40)
            
            rate_readout = "%.2f" % event_rate +"+/-" + "%.2f" % event_rate_std +" Hz"
            
            if event_rate>= 100.:
                rate_readout = "%.2f" % event_rate +"+/-" + "%.2f" % event_rate_std 
                
            if event_rate_std < 0.02:#if len(rate_readout)*8 < 112:
                rate_readout = "%.3f" % event_rate +"+/-" + "%.3f" % event_rate_std +" Hz"
                if event_rate>= 10.:
                    rate_readout = "%.2f" % event_rate +"+/-" + "%.2f" % event_rate_std +" Hz"
                    if event_rate>= 100.:
                        rate_readout = "%.2f" % event_rate +"+/-" + "%.2f" % event_rate_std +""
                    
            d.display.text(rate_readout,int((128- (len(rate_readout) * 8))/2),50)
        
        d.display.show()
        
        e.Deadtime += time_diff(micros(),td1)
        
        

def trigger_Detector(d,e):
    e.ADC_value_1    = d.ADC1.read_u16()

    d.CoincidencePinOutput.high() # takes 11us
    
    for i in range(3):
      if d.CoincidencePinInput.value() == 1:
          e.Coincident = 1
        
    d.CoincidencePinOutput.low()
    
    if e.Coincident == 1:
        e.CoincidentEventNumber += 1
    
    turn_on_LEDs(d,e)
        
    td1 = micros()
    
    e.Timestamp    = time_diff(millis(),d.start_time)
    e.ADC_value_1    = math.ceil((e.ADC_value_1+1)/16)-1
    e.ADC_value_2    = math.ceil((e.ADC_value_2+1)/16)-1
    e.SiPM_pulse_amplitdue = get_SiPM_peak_voltage(e.ADC_value_1,e.ADC_value_2)
    e.EventNumber     +=1

    td2 = micros()
    e.Deadtime    += (time_diff(td2,td1)) + 20 
    d.TotalDeadtime += e.Deadtime/1000.
    write_to_microsd(d,e)
    write_to_serial(d,e)
    e.Deadtime = 0
    #d.ResetTrigger.high()
    #if e.Coincident == 1:
    turn_off_LEDs(d,e)
    #d.ResetTrigger.low()
    e.Coincident = 0
    
    e.Deadtime    += (time_diff(micros(),td2))
    

def sleep(s):
    return time.sleep(s)
def sleep_ms(ms):
    return time.sleep_ms(ms)
def sleep_us(us):
    return time.sleep_us(us)
def micros():
    return time.ticks_us()
def millis():
    return time.ticks_ms()

def time_diff(ticks1,ticks2):
    return time.ticks_diff(ticks1, ticks2) # This function accounts for wrap around.

def setup_detector_name(d):
    file = open("detectorName.txt", "r")
    d.DetectorName = file.readline()
    if len(d.DetectorName)>16:
        print('Detector Name is too long, set it to shorter than 16 characters')
        d.DetectorName = "DetNameIsToLong"
    file.close()
    
def scan_I2CDevices(d):
    i2c=I2C(1,sda=Pin(14), scl=Pin(15), freq=400000)
    devices = i2c.scan()
    expected_devices = [60,118]
    for device in devices:
        if device in expected_devices:
            if d.VERBOSE:
                if device == 60:
                    print("# BMP280 Temp/Press Sensor: Decimal address: ",device," | Hexa address: ",hex(device))
                if device == 118:
                    print("# OLED 0.96: Decimal address: ",device," | Hexa address: ",hex(device))
        else:
            if d.VERBOSE:
                print("# Unknown: Decimal address: ",device," | Hexa address: ",hex(device))

def check_CoincidentDetector(d,e):

    d.CoincidencePinInput = Pin(d.CoincidencePin1, mode = Pin.IN)
    if d.CoincidencePinInput.value() == 1:
        d.CoincidencePinOutput = Pin(d.CoincidencePin2, mode = Pin.OUT)
        d.CoincidencePinOutput.high()
        d.LED_5mm.duty_u16(int(100 * 65535/100.))
        d.LED_3mm.duty_u16(int(100 * 65535/100.))
        time.sleep(1)
        d.LED_5mm.duty_u16(0)
        d.LED_3mm.duty_u16(0)
        d.CoincidencePinOutput.low()
        d.COINCIDENCE      = True     
        if d.VERBOSE:
            print("# Coincidence detector found.")
    else:
        d.CoincidencePinOutput = Pin(d.CoincidencePin1, mode = Pin.OUT)
        d.CoincidencePinOutput.high()
        d.CoincidencePinInput = Pin(d.CoincidencePin2, mode = Pin.IN)
        counter = 0
        for i in range(100):
            time.sleep(0.01)
            if d.CoincidencePinInput.value() == 1:
                counter+=1
                if counter > 5:
                    d.LED_5mm.duty_u16(int(100 * 65535/100.))
                    d.LED_3mm.duty_u16(int(100 * 65535/100.))
                    
                    time.sleep(1)
                    d.LED_5mm.duty_u16(0)
                    d.LED_3mm.duty_u16(0)
                    d.CoincidencePinOutput.low()
                    d.COINCIDENCE      = True
                    if d.VERBOSE:
                        print("# Coincidence detector found.")
                    #break
            
    
def setup_BMP280Sensor(d,e):
    i2c = I2C(1,sda=Pin(14), scl=Pin(15), freq=400000)
    d.bmp = BMP280(i2c, 0x76)
    d.bmp.use_case(BMP280_CASE_WEATHER)
    d.bmp.oversample(BMP280_OS_HIGH)
    d.bmp.temp_os = BMP280_TEMP_OS_8
    d.bmp.press_os = BMP280_PRES_OS_4
    d.bmp.standby = BMP280_STANDBY_250
    d.bmp.iir = BMP280_IIR_FILTER_2
    d.bmp.spi3w = BMP280_SPI3W_ON
    d.bmp.sleep()
    e.Temperature = d.bmp.temperature
    e.Pressure    = d.bmp.pressure
    if d.VERBOSE:
        print("# Temperature " +str(e.Temperature) +"C")
        print("# Pressure " + str(e.Pressure)+"Pa")
        
        
    d.bmp.power_mode = BMP280_POWER_NORMAL
    
    '''
    start_time = time.ticks_ms()  # time when measurement starts
    bmp.force_measure()
    end_time = time.ticks_ms()  # time when it ends
    measurement_time = time.ticks_diff(end_time, start_time)  # time taken for the measurement
    print("Time taken for bmp.force_measure():", measurement_time, "ms")
    print("Measuring:", bmp.is_measuring)
    print("Updating:", bmp.is_updating)
    '''



    
    

    
def setup_buzzer(d):
    if d.Buzzer:
        buzzer = PWM(d.BuzzerPin)
        tones = {
        "B0": 31,
        "C1": 33,
        "CS1": 35,
        "D1": 37,
        "DS1": 39,
        "E1": 41,
        "F1": 44,
        "FS1": 46,
        "G1": 49,
        "GS1": 52,
        "A1": 55,
        "AS1": 58,
        "B1": 62,
        "C2": 65,
        "CS2": 69,
        "D2": 73,
        "DS2": 78,
        "E2": 82,
        "F2": 87,
        "FS2": 93,
        "G2": 98,
        "GS2": 104,
        "A2": 110,
        "AS2": 117,
        "B2": 123,
        "C3": 131,
        "CS3": 139,
        "D3": 147,
        "DS3": 156,
        "E3": 165,
        "F3": 175,
        "FS3": 185,
        "G3": 196,
        "GS3": 208,
        "A3": 220,
        "AS3": 233,
        "B3": 247,
        "C4": 262,
        "CS4": 277,
        "D4": 294,
        "DS4": 311,
        "E4": 330,
        "F4": 349,
        "FS4": 370,
        "G4": 392,
        "GS4": 415,
        "A4": 440,
        "AS4": 466,
        "B4": 494,
        "C5": 523,
        "CS5": 554,
        "D5": 587,
        "DS5": 622,
        "E5": 659,
        "F5": 698,
        "FS5": 740,
        "G5": 784,
        "GS5": 831,
        "A5": 880,
        "AS5": 932,
        "B5": 988,
        "C6": 1047,
        "CS6": 1109,
        "D6": 1175,
        "DS6": 1245,
        "E6": 1319,
        "F6": 1397,
        "FS6": 1480,
        "G6": 1568,
        "GS6": 1661,
        "A6": 1760,
        "AS6": 1865,
        "B6": 1976,
        "C7": 2093,
        "CS7": 2217,
        "D7": 2349,
        "DS7": 2489,
        "E7": 2637,
        "F7": 2794,
        "FS7": 2960,
        "G7": 3136,
        "GS7": 3322,
        "A7": 3520,
        "AS7": 3729,
        "B7": 3951,
        "C8": 4186,
        "CS8": 4435,
        "D8": 4699,
        "DS8": 4978
        }
        
        song = ["E5","G5","A5","P","E5","G5","B5","A5","P","E5","G5","A5","P","G5","E5"]
        
        def playtone(frequency):
            buzzer.duty_u16(1000)
            buzzer.freq(frequency)
        
        def bequiet():
            buzzer.duty_u16(0)
        
        def playsong(mysong):
            for i in range(len(mysong)):
                if (mysong[i] == "P"):
                    bequiet()
                else:
                    playtone(tones[mysong[i]])
                sleep(0.4)
            bequiet()
            
        playsong(song)
    

def setup_ADC(d):
    d.ADC1 = ADC(d.SignalPin1) #low gain
    d.ADC2 = ADC(d.SignalPin2) #high gain
    

def setup_GPIO(d):
    d.LED_3mm = PWM(Pin(d.LEDPin1))
    d.LED_3mm.freq(1000)
    d.LED_5mm = PWM(Pin(d.LEDPin2))
    d.LED_5mm.freq(1000)
    d.Trigger = Pin(d.Trigger, Pin.IN)
    Pin(2, Pin.IN)
    Pin(3, Pin.IN)
    Pin(4, Pin.IN)
    Pin(5, Pin.IN)
    
    d.ResetTrigger = Pin(d.ResetPin, Pin.OUT, value = 0)
    Pin(Pin(23), Pin.IN)
    #PWM(Pin(23))
    
def setup_signal_treshold(d):
    d.TriggerThreshold = int(d.SignalThreshold *16)
 
def setup_OLED(d):
    if d.OLED:
        i2c=I2C(1,sda=Pin(d.OLED_SDA), scl=Pin(d.OLED_SCL), freq=400000)
        display = SSD1306_I2C(128, 64, i2c)
        display.rotate(False)
        display.hline(0, 8, 4, 1)
        display.show()
        d.display = display

    
def OLEDSlashScreen(d):
    if d.OLED:
        buffer = bytearray(b"BM>\x04\x00\x00\x00\x00\x00\x00>\x00\x00\x00(\x00\x00\x00\x80\x00\x00\x00@\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x04\x00\x00\xc4\x0e\x00\x00\xc4\x0e\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xc1\xc0\xf0\x1c\x07|\x06\x07\x00\x00\x00\x00\x00\x00\x00\x01\xc1\xc1\xf8>\x07\xfe\x06\x07\x00\x00\x00\x00\x00\x00\x00\x01\xc1\xc3\xfe\x7f\x07\xce\x0f\x0f\x80\x00\x00\x00\x00\x00\x00\x01\xc1\xc7\x1f'\x07\x8e\x0f\x0f\x80\x00\x00\x00\x00\x00\x00\x01\xc1\xc6\x0f\x07\x07\x1e\x1f\x0f\xc0\x00\x00\x00\x00\x00\x00\x01\xc1\xc4\x07\x07\x07<\x1f\x9f\xc0\x00\x00\x00\x00\x00\x00\x01\xc1\xc0\x07\x07\x07\xf8\x1f\x9f\xc0\x00\x00\x00\x00\x00\x00\x01\xc1\xc0\x07\x07\x07\xe09\x99\xe0\x00\x00\x00\x00\x00\x00\x01\xc3\xc3\x07\x07\x07\x8c9\xf9\xe0\x00\x00\x00\x00\x00\x00\x01\xe7\xc7\x8f\x07\x07\x0e9\xf9\xe0\x00\x00\x00\x00\x00\x00\x01\xff\xc7\x8e\x07\x07\x1ep\xf0\xf0\x00\x00\x00\x00\x00\x00\x00\xff\xc3\x9c?\xe3\xfcp\xf0\xf0\x00\x00\x00\x00\x00\x00\x00}\xc1\xf0?\xe1\xf8p\xf0\xf0\x00\x00\x00\x00\x00\x00\x00\x01\xc0\x00\x07\x80\x00\xe0`x\x00\x00\x00\x00\x00\x00\x00\x01\xc0\x00\x07\x00\x00\xe0`x\x00\x00\x00\x00\x00\x00\x00\x01\xc0\x00\x06\x00\x00\xe0`x\x00\x00\x00\x01\x00\x00\x00\x01\xc0\x00\x04\x00\x01\xc0@<\x00\x00\x00\x03\xff\x80\x00\x01\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x81\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xff\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\xff\xf0 \x00\x00\x00\x00x\x0e\x1c<8>\x00\xe0\x0f\x03\xf8\x7f\x80\x00\x00\x00\xfc\x0e\x1c<8\x7f\x03\xf8\x1c \xfc \x00\x00\x00\x01\xff\x0e\x1c<8\xf7\x8f\xbe8`~\x00\x00\x00\x00\x03\x8f\x8e\x1c<8\xe1\x8f\x1e0`>\x08\x00\x00\x00\x03\x07\x8e\x1c<8\xe0\x1f\x1f\x00\xf0\x1f\x1f\x80\x00\x00\x02\x03\x8e\x1c<8\xf8\x1e\x0f\x00\xf8\x1f\x08\x00\x00\x00\x00\x03\x8e\x1c<8|\x1e\x0f\x00\xfc\x0f\x00\x00\x00\x00\x00\x03\x8e\x1c<8?\x1e\x0f\x00:\x0f\x04\x00\x00\x00\x01\x83\x8e\x1c<8\x0f\x9e\x0f\x00\x11\x8f\x0f\x80\x00\x00\x03\xc7\x8e\x1c<8\x03\x9f\x1f\x00\x00\xcf\x04\x00\x00\x00\x03\xc7\x0e\x1e\xfe\xf8\xc3\x8f\x1e\x00\x00\xef\x00\x00\x00\x00\x01\xce\x0e\x1f\xff\xf8\xe7\x0f\xbe\x00\x03\xef\x08\x00\x00\x00\x00\xf8\x0e\x0f\xcf\xb8~\x03\xf8\x10\x07\xdf\x1f\x80\x00\x00\x00\x00\x00\x07\x878<\x00\xe0\x08\x0f\xde\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x000?\xbe\x00\x00\x00\x00\x00\x00\x0e\x00\x00\x00\x00\x00\x0083| \x00\x00\x00\x00\x00\x0e\x00\x00\x00\x00\x00\x00\x1c<\xf8\x7f\x80\x00\x00\x00\x00\x0e\x00\x00\x00\x00\x00\x00\x0f\x03\xf0 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\xff\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xff\x81\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xff\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        buffer = bytearray(buffer)
        buffer = bytearray([buffer[ii] for ii in range(len(buffer) - 1, -1, -1)])
        img_xsize = 128
        img_ysize = 64
        fb = framebuf.FrameBuffer(buffer, img_xsize, img_ysize, framebuf.MONO_HMSB)
        d.display.fill(0)  # Clear screen
        d.display.blit(fb, 0, 0)
        d.display.rotate(False)# Draw logo
        d.display.show()
    
    

        
def setup_microSD(d, fileprefix = "CW_"):
    # Setup the microSD Card writer. The SensePin tells you if a physical SD card is ins
    cs = machine.Pin(d.SD_CS, machine.Pin.OUT) # Chip select
    spi = machine.SPI(1, # reading from SPI1
              baudrate=1000000,
              polarity=0,
              phase=0,
              bits=8,
              firstbit=machine.SPI.MSB,
              sck=machine.Pin(d.SD_SCK), # clock
              mosi=machine.Pin(d.SD_TX), # transmit
              miso=machine.Pin(d.SD_RX)) # receive

    SD_sense_pin = Pin(d.SD_Detect, Pin.IN, Pin.PULL_UP)
    if SD_sense_pin.value()==1:
        if d.VERBOSE:
            print("# No MicroSD card inserted.")
        d.is_SDAvailable = False
    elif SD_sense_pin.value()==0:
        if d.VERBOSE:
            print("# MicroSD card inserted.")
        d.SD = sdcard.SDCard(spi, cs)
        d.is_SDAvailable = True
    
        vfs = uos.VfsFat(d.SD)
        uos.mount(vfs, "/sd")
      
        #print(os.listdir())
        def file_or_dir_exists(filename):
            try:
                os.stat(filename)
                return True
            except OSError:
                return False
        sd_contents = os.listdir("/sd")
        #print(sd_contents)
        for i in range(1, 1001):
            hundreds = (i // 100) % 10
            tens = (i // 10) % 10
            ones = i % 10

            microSD_filename = f"File_{hundreds}{tens}{ones}"
            
            if d.COINCIDENCE:
                filename = "C_" + fileprefix + str(microSD_filename)+".txt"
            else:
                filename = "M_" + fileprefix + str(microSD_filename)+".txt"
            
            # Checking if the file with the generated filename already exists
            if filename in sd_contents:
                continue

            else:
                break
            
        if d.VERBOSE:
            print('# Creating file on MicroSD card: ',filename)
        
        d.microSD_filename = '/sd/'+filename
        
    if d.is_SDAvailable == True:
        d.sd_file = open(d.microSD_filename, "w")
    

def write_microSD_header(d):
    if d.is_SDAvailable == True:
        d.sd_file.write("###################################################################################################\r")
        d.sd_file.write("### CosmicWatch: The Desktop Muon Detector\r")
        d.sd_file.write("### Device ID: " + str(d.DetectorName) +"\r")
        #d.sd_file.write("### Launch time: " + str(d.DetectorName) +"\r")
        d.sd_file.write("### Questions? Email Spencer N. Axani (saxani@udel.edu)\r")
        d.sd_file.write("### Event TimeStamp[ms] ADC1 ADC2 SiPM[mV] Temp[C] Pressure[Pa] DeadTime[us] Coincident Name\r")
        d.sd_file.write("###################################################################################################\r")

def print_serial_header(d):
    print("###################################################################################################\r")
    print("### CosmicWatch: The Desktop Muon Detector\r")
    print("### Device ID: " + str(d.DetectorName) +"\r")
    #print("### Launch time: " + str(d.DetectorName) +"\r")
    print("### Questions? Email Spencer N. Axani (saxani@udel.edu)\r")
    print("### Event TimeStamp[ms] ADC1 ADC2 SiPM[mV] Temp[C] Pressure[Pa] DeadTime[us] Coincident Name\r")
    print("###################################################################################################\r")

def turn_on_LEDs(d,e):
    if e.Coincident == 1:
        d.LED_5mm.duty_u16(int(d.LEDBrightness * 65535/100.))
        d.LED_3mm.duty_u16(int(d.LEDBrightness * 65535/100.))
    else:
        d.LED_5mm.duty_u16(int(d.LEDBrightness * 65535/100.))
        
def turn_off_LEDs(d,e):
    d.LED_5mm.duty_u16(0)
    d.LED_3mm.duty_u16(0)
    



def calculate_baseline_voltages(d):
    # Calulating basleine voltage
    baseline_samples = 1000
    
    baseline_sum = 0
    baseline_values_ADC_1 = []
    #baseline_values_ADC_2 = []
    
    for _ in range(baseline_samples):
        #analog_val = analog_pin.read_u16()
        baseline_values_ADC_1.append(d.ADC1.read_u16())
        #baseline_values_ADC_2.append(d.ADC2.read_u16())
        #baseline_sum = baseline_sum + analog_val
        #utime.sleep(0.0001)
    baseline_voltage_1 = sum(baseline_values_ADC_1)/1000
    #baseline_voltage_2 = sum(baseline_values_ADC_2)/1000
    #baseline_voltage_std = np.std(baseline_values)
    
    
    print("Baseline voltage_1", baseline_voltage_1 * 3300/2**12, "+/-")
    #print("Baseline voltage_2", baseline_voltage_2 * 3300/2**12, "+/-")

'''
def Timer_callback(timer):
    UpdateOLED(d, e)  # Call the function to update the OLED display
    
# Initialize the timer
Timer.init(mode=Timer.PERIODIC, period=333,  callback=Timer_callback(timer))  # Period set for 333 ms (3 times per second)
#threading.Timer(1/3, update_oled).start()
#print('oled', time_diff(millis(),t1)) 

'''

# verify all the events are correctly recorded at some frequency

