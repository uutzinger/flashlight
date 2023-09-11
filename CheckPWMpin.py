#!/usr/bin/python3

##########################################################
# Front Light PWM Intensity Modulator
#
# Urs Utzinger, Spring 2023
###########################################################

import math
import board     # circuit python
import digitalio # circuit python
import pwmio     # circuit python
import logging
import argparse
import os
import signal

###########################################################
# Configs for NEOPIXEL strip(s)
###########################################################

PWM_PIN       = board.D13 # PWM pin, use same pin for left and right light
PWM_FREQUENCY = 500       # 100Hz .. 1kHz   

BRIGHTNESS    = 0.25
HUMINTENFRAC  = 0.3
HUMINTERVAL   = 3.0 # sec

###########################################################
# Constants
###########################################################

TWOPI   = 2.0 * math.pi
PIHALF  = math.pi / 2.0
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
EPSILON = 2.0*math.ldexp(1.0, -53)

##############################################################################################
# MAIN
##############################################################################################

# Setup logging
logger = logging.getLogger(__name__)
logger.log(logging.INFO, 'Starting Flashlight...')

intensity = 10
pin = pwmio.PWMOut(PWM_PIN, frequency=PWM_FREQUENCY, duty_cycle=0)
pin.duty_cycle = int(intensity / 100. * 65535) 

