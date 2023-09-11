#!/usr/bin/python3

##########################################################
# Front Light PWM Intensity Modulator
#
# Urs Utzinger, Fall 2023
###########################################################

import board     # circuit python
import pwmio     # circuit python
import logging

###########################################################
# Configs for NEOPIXEL strip(s)
###########################################################

PWM_PIN       = board.D13 # PWM pin, use same pin for left and right light
PWM_FREQUENCY = 500       # 100Hz .. 1kHz   

##############################################################################################
# MAIN
##############################################################################################

# Setup logging
logger = logging.getLogger(__name__)
logger.log(logging.INFO, 'Starting Flashlight...')

intensity = 25. / 100.
pin = pwmio.PWMOut(PWM_PIN, frequency=PWM_FREQUENCY, duty_cycle=0)
pin.duty_cycle = int(intensity * 65535) 

