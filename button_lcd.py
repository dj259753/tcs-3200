#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Description : Reads RGB values from a TCS3200 colour sensor and write the result into a CSV file.
# Use with switch buttons and standard HD44780 LCD display.
# Usage : ./button_lcd.py
# Licence : Public Domain
# Versioning : https://github.com/CedricGoby/rpi-tcs3200
# Script that allows to run pigpiod as a Linux service with root privileges : https://github.com/joan2937/pigpio/tree/master/util
# Python Library for LCD : https://github.com/adafruit/Adafruit_Python_CharLCD
#
# Before starting the script pigpiod must be running and the Pi host/port must be specified.
#
# sudo pigpiod (or use a startup script)
# export PIGPIO_ADDR=hostame (or use the pigpio.pi() function)
# export PIGPIO_PORT=port (or use the pigpio.pi() function)
# Import LCD module

if __name__ == "__main__":

   import sys
   import pigpio
   import tcs3200
   import os
   import time
   import mail
   from os import system
   
   global _re
   system("PIGPIO_ADDR=hostame")
   system("PIGPIO_PORT=port")
   
   # specify the Pi host/port.  For the remote / name, use '' if on local machine
   pi = pigpio.pi('', 8888)

   capture = tcs3200.sensor(pi, 24, 22, 23, 4, 17, 18)

   capture.set_frequency(2) # 20%
   interval = 1 # Reading interval in second
   capture.set_update_interval(interval)

   _led_on = capture._led_on
   _led_off = capture._led_off
    
   _reading = capture._reading
   _identify = capture._fruit_identify
   _csv_output_fruit = capture._csv_output_fruit
   _csv_output_decay = capture._csv_output_decay
   
   _file_output = "Fruit_reading.csv" # Name of the output csv file
   _file_output_decay = "Fruit_decay.csv"
   
   _detect_decay = capture._detect_decay
   GPIO = tcs3200.GPIO
   _setup_buttons = tcs3200._setup_buttons()
   _create_picture = capture._create_picture
   lcd = tcs3200.lcd
   
   _display_menu = True # State of the menu
   while True:
      if _display_menu:
          lcd.clear()
          print("System ready... \n1.Identify Fruits\n2.Detect Decay \n3.Send report\n")
          lcd.message("System ready... \n1.Identify Fruits\n2.Detect Decay \n3.Send report")
          _display_menu = False # Display menu only once in the loop
      
      if(GPIO.input(20) == GPIO.LOW):
          time.sleep(0.1)
          print("Place a fresh fruit in the box\n\n")
          lcd.clear()
          lcd.message("Place a fresh fruit in the box\nKey 1: continue.\nKey 2: Main menu.")
          while True    :          
              if(GPIO.input(20) == GPIO.LOW):
                  
                  _led_on()
                  _reading()
                  _csv_output_fruit(_file_output)
                  _led_off()
                  break
              elif(GPIO.input(21) == GPIO.LOW):
                  break
         
          _display_menu = True
          time.sleep(0.1)
	  
      elif(GPIO.input(21) == GPIO.LOW):
          time.sleep(0.1)
          print("Please choose a Fruit to detect.\n1: Banana\n2: Quit\n\n\n")
          lcd.clear()
          lcd.message("Please choose a Frui\nt to detect.\n1: Banana\n2: Main menu.")
          while True    :          
              if(GPIO.input(20) == GPIO.LOW):
                  _led_on()
                  _re = 1
                  _reading()
                  _csv_output_decay(_file_output_decay)
                  _led_off()
                  break
              elif(GPIO.input(21) == GPIO.LOW):
                  break
          _display_menu = True
          time.sleep(0.1)
	  
      elif(GPIO.input(18) == GPIO.LOW):
          _led_off()
          lcd.clear()
          lcd.message("Sending mail...")
          time.sleep(1)
          mail.send_mail()
          lcd.clear()
          lcd.message("Report has been send successfully.")
          time.sleep(5)
          _display_menu = True
