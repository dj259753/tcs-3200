#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Description : Reads RGB values from a TCS3200 colour sensor and write the result into a CSV file.
# Usage : ./tcs3200.py
# Licence : Public Domain
# Versioning : https://gitlab.com/CedricGoby/rpi-tcs3200
# Original script : http://abyz.co.uk/rpi/pigpio/index.html
# Script that allows to run pigpiod as a Linux service with root privileges : https://github.com/joan2937/pigpio/tree/master/util
#
# Before starting the script pigpiod must be running and the Pi host/port must be specified.
#
# sudo pigpiod (or use a startup script)
# export PIGPIO_ADDR=hostame (or use the pigpio.pi() function)
# export PIGPIO_PORT=port (or use the pigpio.pi() function)

from __future__ import print_function

from blessings import Terminal
term = Terminal()

import os
import pigpio
import time
import threading
import csv
import colorsys
# Buttons
import RPi.GPIO as GPIO


# Setup GPIO for buttons
def _setup_buttons():
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Setup button 1,input,  BCM 20
  GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Setup button 2,input,  BCM 21
  GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Setup button 3,input,  BCM 18
  if(GPIO.input(20) == GPIO.LOW):
        time.sleep(0.1)   #wait for 0.1 s
        lcd.clear()
        lcd.message("Did you pressed the button?")  #lcd display 
        
# Import LCD module
import Adafruit_CharLCD as LCD

# LCD PIN = PI PIN (BCM)
lcd_rs        = 5
lcd_en        = 6
lcd_d4        = 26
lcd_d5        = 16
lcd_d6        = 12
lcd_d7        = 13
lcd_backlight = 19

# Define LCD column and row size for 20x4 LCD.
lcd_columns = 20
lcd_rows    = 4

# Initialize the LCD using the pins above.
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,
                        lcd_columns, lcd_rows, lcd_backlight)


"""
This class reads RGB values from a TCS3200 colour sensor.

VDD   Supply Voltage (2.7-5.5V).
GND   Ground.
OE    Output enable.
LED   LED control.
GND   Ground (LED).
S0/S1 Output frequency scale selection.
S2/S3 Colour filter selection.
OUT   Output frequency square wave.
OE    Output enable, active low. When OE is high OUT is disabled allowing multiple sensors to share the same OUT line.
LED   If you want to turn on the LEDs on the board, you could connect the led pin to 5v or a digital pin to drive them. 
OUT   is a square wave whose frequency is proportional to the intensity of the selected filter colour.
S0/S1 scales the frequency at 100%, 20%, 2% or off.
S2/S3 selects between red, green, blue, and no filter. To take a reading the colour filters are selected in turn for a fraction of a second and the frequency is read and converted to Hz.
"""
class sensor(threading.Thread):
   """
   The gpios connected to the sensor OUT, S2, and S3 pins must be specified.
   The S0, S1 (frequency) and OE (output enable) gpios are optional.
   
   This script uses BCM numbers.
   
   TCS3200     |   GPIO (physical)   |   GPIO (BCM)   
   S0          |          7          |      BCM 4
   S1          |         11          |      BCM 17
   S2          |         15          |      BCM 22
   S3          |         16          |      BCM 23
   OUT         |         18          |      BCM 24
   VDD         |          1          |      5V Power
   LED         |         22          |      BCM 25
   GND         |          6          |      Ground
   """
   
   def __init__(self, pi, OUT, S2, S3, S0=None, S1=None, OE=None):
   
      threading.Thread.__init__(self)
      
      self._pi = pi
      self._OUT = OUT
      self._S2 = S2
      self._S3 = S3

      self._mode_OUT = pi.get_mode(OUT)
      self._mode_S2 = pi.get_mode(S2)
      self._mode_S3 = pi.get_mode(S3)

      """
      Disable frequency output (OUT).
      """
      pi.write(OUT, 0)
      
      """
      Disable colour filter selection (S2 S3).
      """     
      pi.set_mode(S2, pigpio.OUTPUT)
      pi.set_mode(S3, pigpio.OUTPUT)

      self._S0 = S0
      self._S1 = S1
      self._OE = OE

      if (S0 is not None) and (S1 is not None):
         self._mode_S0 = pi.get_mode(S0)
         self._mode_S1 = pi.get_mode(S1)
         """
         Enable S0/S1 Output frequency scale selection
         """        
         pi.set_mode(S0, pigpio.OUTPUT)
         pi.set_mode(S1, pigpio.OUTPUT)

      if OE is not None:
         self._mode_OE = pi.get_mode(OE)
         pi.set_mode(OE, pigpio.OUTPUT)
         """
         Enable device (active low).
         """
         pi.write(OE, 0)

      self.set_sample_size(20)

      """
      One reading per second.
      """
      self.set_update_interval(1.0)

      """
      S0/S1 2% Frequency scale selection.
            The higher the frequency the faster the response. If you go from setting 1 (2%) to setting 2 (20%) the readings may be faster.
            if (self._S0 is not None) and (self._S1 is not None)
      """
      self.set_frequency(3)

      """
      S2/S3 Clear (no colour filter).
      """
      self._set_filter(3) # Clear.

      self._rgb_black = [0]*3
      self._rgb_white = [10000]*3

      self.hertz=[0]*3 # Latest triplet.
      self._hertz=[0]*3 # Current values.

      self._delay=[0.1]*3 # Tune delay to get _samples pulses.

      self._cycle = 0

      self._cb_OUT = pi.callback(OUT, pigpio.RISING_EDGE, self._cbf)
      self._cb_S2 = pi.callback(S2, pigpio.EITHER_EDGE, self._cbf)
      self._cb_S3 = pi.callback(S3, pigpio.EITHER_EDGE, self._cbf)

      self.daemon = True

      self.start()
      
      
   def _led_on(self):
      
      self._pi.set_mode(25, pigpio.OUTPUT)
      self._pi.write(25, 1)
      time.sleep(1)

   # LED Off
   def _led_off(self):
      
      self._pi.set_mode(25, pigpio.OUTPUT)
      self._pi.write(25,0)
      time.sleep(1)


   def cancel(self):
      """
      Cancel the sensor and release resources.
      """
      self._cb_S3.cancel()
      self._cb_S2.cancel()
      self._cb_OUT.cancel()

      self.set_frequency(0) # off

      self._set_filter(3) # Clear

      self._pi.set_mode(self._OUT, self._mode_OUT)
      self._pi.set_mode(self._S2, self._mode_S2)
      self._pi.set_mode(self._S3, self._mode_S3)

      if (self._S0 is not None) and (self._S1 is not None):
         self._pi.set_mode(self._S0, self._mode_S0)
         self._pi.set_mode(self._S1, self._mode_S1)

      if self._OE is not None:
         self._pi.write(self._OE, 1) # disable device
         self._pi.set_mode(self._OE, self._mode_OE)

   def get_rgb(self, top=255):
      """
      Get the latest RGB reading.

      The raw colour hertz readings are converted to RGB values as follows.
      RGB = 255 * (Sample Hz - calibrated black Hz) / (calibrated white Hz - calibrated black Hz)

      By default the RGB values are constrained to be between 0 and 255. A different upper limit can be set by using the top parameter.
      """
      rgb = [0]*3
      s = [13335, 12500, 20500]  #top frequency of [red, green, blue]
      for c in range(3):         #repeat three times for each RGB channel
         v = self.hertz[c] - 0  
         p = top * v / s[c]      #achieve the formula
         if p < 0:
            p = 0
         elif p > top:           #limit the value between 0 and 255.
            p = top
         rgb[c] = p
      
      return rgb[:]
    
   def _get_colorsys(self):
     yiq = [0]*3
     self.r, self.g, self.b = self.get_rgb()                        #get rgb value
     yiq = colorsys.rgb_to_yiq(self.r/255, self.g/255, self.b/255)  #get yiq value
     hsv = colorsys.rgb_to_hsv(self.r/255, self.g/255, self.b/255)  #get hsv value
     self.y, self.i, self.q = yiq
     self.h, self.l, self.s = hls
     self.h1, self. s1, self. v1 = hsv
     print([self.y] + [self.i] + [self.q] )                         #print YIQ result
     return yiq[:]
   """
   Get the latest hertz reading.
   """
   def get_hertz(self):
      return self.hertz[:]
 

   """
   Set the frequency scaling.
   
   f  S0  S1  Frequency scaling
   0  L   L   Off
   1  L   H   2%
   2  H   L   20%
   3  H   H   100%
   """
   def set_frequency(self, f):

      if f == 0: # off
         S0 = 0; S1 = 0
      elif f == 1: # 2%
         S0 = 0; S1 = 1
      elif f == 2: # 20%
         S0 = 1; S1 = 0
      else: # 100%
         S0 = 1; S1 = 1

      if (self._S0 is not None) and (self._S1 is not None):
         self._frequency = f
         self._pi.write(self._S0, S0) # BCM 4, set S0 
         self._pi.write(self._S1, S1) # BCM 17, set S1
      else:
         self._frequency = None

   """
   Get the current frequency scaling.
   """
   def get_frequency(self):
      return self._frequency

   """
   Set the interval between RGB updates.
   """
   def set_update_interval(self, t):
      if (t >= 0.1) and (t < 2.0):
         self._interval = t

   """
   Get the interval between RGB updates.
   """
   def get_update_interval(self):
      return self._interval

   """
   Set the sample size (number of frequency cycles to accumulate).
   """
   def set_sample_size(self, samples):
      if samples < 20:
         samples = 20
      elif samples > 200:
         samples = 200

      self._samples = samples

   """
   Set the sample size (number of frequency cycles to accumulate).
   """
   def get_sample_size(self):
      return self._samples

   """
   Pause reading (until a call to resume).
   """
   def pause(self):
      self._read = False

   """
   Resume reading (after a call to pause).
   """
   def resume(self):
      self._read = True

   """
   Set the colour to be sampled.
   
   f  S2  S3  Photodiode
   0  L   L   Red
   1  H   H   Green
   2  L   H   Blue
   3  H   L   Clear (no filter)
   """
   def _set_filter(self, f):

      if f == 0: # Red
         S2 = 0; S3 = 0
      elif f == 1: # Green
         S2 = 1; S3 = 1
      elif f == 2: # Blue
         S2 = 0; S3 = 1
      else: # Clear
         S2 = 1; S3 = 0
				
      self._pi.write(self._S2, S2); self._pi.write(self._S3, S3)

   def _cbf(self, g, l, t):

      if g == self._OUT:  # if the measured pin is OUT pin
         if self._cycle == 0:      #if this is the first period
            self._start_tick = t   #assign measured time to _start_tick
         else:
            self._last_tick = t    #assign measured time to _last_tick
         self._cycle += 1          #the next period 

      else: # Must be transition between colour samples.
         if g == self._S2:
            if l == 0: # Clear -> Red.
               self._cycle = 0
               return
            else:      # Blue -> Green.
               colour = 2
         else:
            if l == 0: # Green -> Clear.
               colour = 1
            else:      # Red -> Blue.
               colour = 0

         if self._cycle > 1:
            self._cycle -= 1
            td = pigpio.tickDiff(self._start_tick, self._last_tick)
            self._hertz[colour] = (1000000 * self._cycle) / td  #according to pigpio library, the unit of tick is 1us. frequency = 1 / period
            self._tally[colour] = self._cycle
         else:
            self._hertz[colour] = 0
            self._tally[colour] = 0

         self._cycle = 0

         # Have we a new set of RGB?
         if colour == 1:
            for i in range(3):
               self.hertz[i] = self._hertz[i]
               self.tally[i] = self._tally[i]

   def run(self):

      self._read = True  #Enalbe read data function
      while True:
         if self._read:  #If read is enabled

            next_time = time.time() + self._interval   #current time + time interval between RGB updates

            self._pi.set_mode(self._OUT, pigpio.INPUT) # Enable output gpio.

            """
            The order Red -> Blue -> Green -> Clear is needed by the callback function so that each S2/S3 transition triggers state change.
            The order was chosen so that a single gpio changes state between each colour to be sampled.
            """
            self._set_filter(0) # Red
            time.sleep(self._delay[0])

            self._set_filter(2) # Blue
            time.sleep(self._delay[2])

            self._set_filter(1) # Green
            time.sleep(self._delay[1])

            self._pi.write(self._OUT, 0) # Disable output gpio.

            self._set_filter(3) # Clear

            delay = next_time - time.time()

            if delay > 0.0:
               time.sleep(delay)

            # Tune the next set of delays to get reasonable results as quickly as possible.

            for c in range(3):

               # Calculate dly needed to get _samples pulses.

               if self.hertz[c]:
                  dly = self._samples / float(self.hertz[c])
               else: # Didn't find any edges, increase sample time.
                  dly = self._delay[c] + 0.1

               # Constrain dly to reasonable values.

               if dly < 0.001:
                  dly = 0.001
               elif dly > 0.5:
                  dly = 0.5

               self._delay[c] = dly

         else:
            time.sleep(0.1)

 

   # Reading (stdout)
   def _reading(self):
            
      for i in range(5): # 5 readings
	        """
	        The first triplet is the RGB values.
	        The second triplet is the PWM frequency in hertz generated for the R, G, and B filters. The PWM frequency is proportional to the amount of each colour.
	        The third triplet is the number of cycles of PWM the software needed to calculate the PWM frequency for R, G, and B.
	        The second and third triplets are only useful during debugging so you needn't worry about them.
	        """
	        self.r, self.g, self.b = self.get_rgb()           #get rgb value
	        self.rhz, self.ghz, self.bhz = self.get_hertz()   #get frequency
	        self.y, self.i, self.q = self._get_colorsys()     #get YIQ value
	        lcd.clear()
	        lcd.message('reading...')           #display: reading...
	        print("Red =" + str(int(self.r)) + "  Green = " + str(int(self.g)) + "  Blue = " + str(int(self.b)))  #print RGB value
	        print("frequency = " + str(int(self.rhz)) + "  " + str(int(self.ghz)) + "  " + str(int(self.bhz)))    #print frequency
	        print("y = " +str(self.y) + "  i = " + str(self.i) + "  q = " + str(self.q))                          #print YIQ value
	        time.sleep(self._interval)        #wait for 'interval' seconds
                  
   # fruit identify
   def _fruit_identify(self):
     self._fruit = ' '
     self.y, self.i, self.q = self._get_colorsys()
     if 0.26 < self.y < 0.3 and 0.02 < self.i < 0.08 and -0.03 < self.q < 0.01:
       print("it's a cucumber")
       lcd.clear()
       lcd.message("This is a cumcuber.\n Price:  0.3￡ each")
       time.sleep(8)
       self._fruit = 'cucumber'
       self._price = '0.2'
     elif 0.36 < self.y < 0.44 and 0.05 < self.i < 0.16 and -0.08 < self.q < 0.01:
         print ("it's a banana")
         lcd.clear()
         lcd.message("This is a banana.\nPrice: 0.19￡ each")
         time.sleep(2)
         self._fruit = 'banana'
         self._price = '0.3'
     elif 0.6 < self.y < 0.8 and 0.22 < self.i < 0.34 and -0.1 < self.q < 0.02:
         print ("it's a lemon")
         lcd.clear()
         lcd.message("This is a lemon.\nPrice: 0.1￡ each.")
         time.sleep(8)
         self._fruit = 'lemon'
         self._price = '0.4'
     elif 0.31 < self.y < 0.49 and 0.17 < self.i < 0.25 and 0.023 < self.q < 0.08:
         print ("it's an apple\nBrand: Pink lady")
         lcd.clear()
         lcd.message("This is an apple.\nBrand: Pink lady.\nPrice: x￡ each")
         time.sleep(8)
         self._fruit = 'Apple / Pink Lady'
         self._price = '0.33'
     elif 0.13 < self.y < 0.23 and 0.04 < self.i < 0.084 and 0 < self.q < 0.03:
         print ("it's a purple onion")
         lcd.clear()
         lcd.message("This is a purple onion\nPrice: x￡ each")
         time.sleep(8)
         self._fruit = 'purple onion'
         self._price = '0.13'
     elif 0.23 < self.y < 0.33 and 0.01 < self.i < 0.08 and -0.07 < self.q < 0.02:
         print ("it's an lime")
         lcd.clear()
         lcd.message("This is a lime\nPrice: x￡ each")
         time.sleep(8)
         self._fruit = 'lime'
         self._price = '0.23'
     elif 0.43 < self.y < 0.5 and 0.15 < self.i < 0.23 and -0.01 < self.q < 0.03:
         print ("it's an white onion")
         lcd.clear()
         lcd.message("This is a white onio\nn\nPrice: 0.1 Pounds ea\nch")
         time.sleep(8)
         self._fruit = 'white onion'
         self._price = '0.14'
     elif 0.26 < self.y < 0.4 and 0.08 < self.i < 0.18 and 0. < self.q < 0.053:
         print ("it's an apple\nBrand:Braeburn apple")
         lcd.clear()
         lcd.message("This is an apple\nBrand: Braeburn apple\nPrice: 0.8￡ each")
         time.sleep(8)
         self._fruit = 'Braeburn Apple'
         self._price = '0.8'
     elif 0.22 < self.y < 0.29 and 0.08 < self.i < 0.17 and 0.01 < self.q < 0.043:
         print ("it's an apple\nBrand:Red apple")
         lcd.clear()
         lcd.message("This is an apple\nBrand: Red apple\nPrice: 1.99￡ each")
         time.sleep(8)
         self._fruit = 'Red Apple'
         self._price = '1.99'
     else :
         print("Please try again.")
         lcd.clear()
         lcd.message("Please try again.")
         time.sleep(6)
         
   
   def _detect_decay(self):
       self.y, self.i, self.q = self._get_colorsys()
       if 0.44 < self.y < 0.54 and 0.04 < self.i < 0.12 and -0.1 < self.q < -0.02:
           print("This banana is not ripe")
           lcd.clear()
           lcd.message("This banana is not ripe")
           time.sleep(8)
           self.decay = 'Not ripe'
       elif 0.47 < self.y < 0.68 and 0.12 < self.i < 0.2 and -0.1 < self.q < 0.05:
           print("This banana is ripe")
           lcd.clear()
           lcd.message("This banana is ripe")
           time.sleep(8)
           self.decay = 'ripe'
       elif 0.13 < self.y < 0.3 and 0 < self.i < 0.08 and -0.1 < self.q < 0.03:
           print("This banana is decayed")
           lcd.clear()
           lcd.message("This banana is decayed")
           time.sleep(8)
           self.decay = 'decay'
       else :
           self.decay = 'not a banana'
           print("this is not a banana")
           lcd.clear()
           lcd.message("This is not a banana")
           time.sleep(8)

   # Write the last reading into a CSV file, add a timestamp (stdout)
   def _csv_output(self, _file_output):
      self.y, self.i, self.q = self._get_colorsys()  #invoke function of getting RGB/colorsys
      try:	   
          with open(_file_output, 'a') as csvfile:   #open/create a csv file
             now=int(time.time())
             timeStruct = time.localtime(now)        #get current local time
             strTime = time.strftime("%Y-%m-%d %H:%M:%S", timeStruct)       #convert time into yyyy-mm-dd-hh-mm-ss format
             capturewriter = csv.writer(csvfile, delimiter='\t')            #write data
             capturewriter.writerow([strTime] + [int(self.r)] + [int(self.g)] + [int(self.b)] + [self.rhz] + [self.ghz] + [self.bhz] + [self.y] + [self.i] + [self.q] )
      except:
          print ("File error !")
      else:
          print("Datas stored\n" + "red = " + str(int(self.r)) + "\ngreen = " + str(int(self.g)) + "\nblue = " + str(int(self.b)))   #hint: success, time.
          time.sleep(0.5)
          
   def _csv_output_fruit(self, _file_output):
      self._fruit_identify()          #invoke function of identifying fruit
      self._am = 1
      try:	   
          with open(_file_output, 'a') as csvfile:    #open/create a csv file
             now=int(time.time())
             timeStruct = time.localtime(now)         #get current local time
             strTime = time.strftime("%Y-%m-%d %H:%M:%S", timeStruct)   #convert time into yyyy-mm-dd-hh-mm-ss format
             print(self._fruit)
             capturewriter = csv.writer(csvfile, delimiter='\t')  
             capturewriter.writerow([strTime] + [self._fruit] + [self._price] + [self._am])  #write data.
      except:
          print ("File error !")
      else:
          lcd.clear()
          lcd.message("Datas stored\n" + str(strTime))
          print("Datas stored\n" + str(strTime))
          time.sleep(5)
          
   #output to csv file, recording fruit ripe status
   def _csv_output_decay(self, _file_output_decay):
      self._detect_decay()
      try:	   
          with open(_file_output_decay, 'a') as csvfile:
             now=int(time.time())
             timeStruct = time.localtime(now)
             strTime = time.strftime("%Y-%m-%d %H:%M:%S", timeStruct)
             print(self.decay)
             capturewriter = csv.writer(csvfile, delimiter='\t')
             capturewriter.writerow([strTime] + [self.decay])
      except:
          print(self.decay)
          print ("File error !")
      else:
          lcd.clear()
          lcd.message("Datas stored\n" + str(strTime))
          print("Datas stored\n" + str(strTime))
          time.sleep(5)
          
   #test frequency
   def _test_frequency(self):
       print (term.bold('\n> frequency test'))       
       while True:
           hz = self.get_hertz()
           self.rhz, self.ghz, self.bhz = self.get_hertz()
           print(str(self.rhz))
           time.sleep(2)
           
   # create a html file with full-screen color.
   def _create_picture(self):
     filename = 'write_data.txt'
     self.r, self.g, self.b = self.get_rgb()
     with open(filename,'w') as f:
       f.write('<body><div style="width: 100%; height: 100%; background-color: rgb(' + str(self.r) + ', ' + str(self.g) + ',' + str(self.b) + ')"></div></body>')
     os.rename('write_data.txt', 'write_data.html')

   #Identify fruit type
