#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Description : Reads RGB values from a TCS3200 colour sensor and write the result into a CSV file.
# Usage : ./stdout.py
# Licence : Public Domain
# Versioning : https://github.com/CedricGoby/rpi-tcs3200
# Script that allows to run pigpiod as a Linux service with root privileges : https://github.com/joan2937/pigpio/tree/master/util
#
# Before starting the script pigpiod must be running and the Pi host/port must be specified.
#
# sudo pigpiod (or use a startup script)
# export PIGPIO_ADDR=hostame (or use the pigpio.pi() function)
# export PIGPIO_PORT=port (or use the pigpio.pi() function)

from __future__ import print_function

if __name__ == "__main__":
   import RPi.GPIO as GPIO
   import sys
   import pigpio
   import time
   import tcs3200
   import os
   from blessings import Terminal


 
   import RPi.GPIO as GPIO
   
   #cancel setup warnings
   GPIO.setwarnings(False)
   #BCM mode
   GPIO.setmode(GPIO.BCM)
   #setup pins
   GPIO.setup(4,GPIO.OUT)
   GPIO.setup(17,GPIO.OUT)
   GPIO.setup(22,GPIO.OUT)
   GPIO.setup(23,GPIO.OUT)
   GPIO.setup(24,GPIO.IN)
   GPIO.setup(25,GPIO.OUT)
   #output/input
   GPIO.output(4,GPIO.HIGH)   '''S0'''
   GPIO.output(17,GPIO.LOW)  '''S1'''
   GPIO.output(22,GPIO.LOW)  '''S2'''
   GPIO.output(23,GPIO.LOW)  '''s3'''
   GPIO.output(25,GPIO.HIGH)  '''led'''
   GPIO.input(18)            '''OUT'''

   
   GPIO = tcs3200.GPIO


   led_on = capture._led_on
   led_on()
##   _set_filter(0)
   while True:
##       print(GPIO.input(24))
      _frequency()
	  
