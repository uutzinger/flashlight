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
import asyncio
import logging
import zmq
import zmq.asyncio
import argparse
import os
import signal
import msgpack
import time

if os.name != 'nt':
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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

def obj2dict(obj):
    '''
    encoding object variables to nested dict
    ''' 
    if isinstance(obj, dict):
        return {k: obj2dict(v) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        return obj2dict(vars(obj))
    elif isinstance(obj, list):
        return [obj2dict(item) for item in obj]
    else:
        return obj

class dict2obj:
    '''
    decoding nested dictionary to object
    '''
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, dict2obj(value))
            else:
                setattr(self, key, value)

flashstate = {"on": 1, "off": 2, "brightness": 3, "hum": 4, "stop": 5}

class flashData(object):
    '''
    FlashLight data
    Sent/Received via ZMQ to control light display
    '''
    def __init__(self, state: int = flashstate["off"], intensity: float = 0.0) -> None:
        self.state = state
        self.intensity = intensity  # Front flashlight intensity

class FlashLight:
    '''
    Flashlight
    Intensity adjustment through PWM on meanwell LED constant current regulator
    '''

    def __init__(self, logger=None):
        self.state = flashstate['off']
        self.intensity = BRIGHTNESS
        self.pin = pwmio.PWMOut(PWM_PIN, frequency=PWM_FREQUENCY, duty_cycle=0)
        self.pin.duty_cycle = int(self.intensity / 100. * 65535) 
        self.logger = logger

    def brightness(self, brightness: float):
        self.intensity = brightness
        if self.state == flashstate['on']:
            self.on()

    def off(self):
        self.state = flashstate["off"]
        self.pin.duty_cycle = 0 

    def on(self):
        self.state = flashstate["on"]
        self.pin.duty_cycle = int(self.intensity / 100. * 65535) 

    async def hum_start(self, stop_event: asyncio.Event, pause_event: asyncio.Event):
        HUMINTENEND   = self.intensity
        HUMINTENSTART = self.intensity * (1. - HUMINTENFRAC)
        HUMINTENINC   = (HUMINTENEND - HUMINTENSTART) / 20.
        INTENSITY     = self.intensity
        INTERVAL      = HUMINTERVAL / 20.
        self.state = flashstate["hum"]
        while not stop_event.is_set():
            HUMINTENEND   = self.intensity
            HUMINTENSTART = self.intensity * (1. - HUMINTENFRAC)
            HUMINTENINC   = (HUMINTENEND - HUMINTENSTART) / 20.
            INTENSITY += HUMINTENINC
            if (INTENSITY > HUMINTENEND) or (INTENSITY < HUMINTENSTART):
                INTENSITYINC = -INTENSITYINC
            else:
                self.pin.duty_cycle = int(INTENSITY / 100. * 65535) 
            await asyncio.sleep(INTERVAL)
        # no more humming
        self.on()


#########################################################################################################
# ZMQ Data Receiver for Flash Light
#########################################################################################################

class zmqWorkerFlash:

    def __init__(self, logger, zmqPort: int = 5554):

        self.dataReady =  asyncio.Event()
        self.finished  =  asyncio.Event()
        self.dataReady.clear()
        self.finished.clear()

        self.logger     = logger
        self.finish_up  = False
        self.paused     = False
        self.zmqPort    = zmqPort

        self.new_neo    = False
        self.timeout    = False

        self.data_neo = flashData()

        self.logger.log(logging.INFO, 'Neopixel zmqWorker initialized')

    async def start(self, stop_event: asyncio.Event):

        self.new_neo = False

        context = zmq.asyncio.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:{}".format(self.zmqPort))

        poller = zmq.asyncio.Poller()
        poller.register(socket, zmq.POLLIN)

        self.logger.log(logging.INFO, 'Flashlight zmqWorker started on {}'.format(self.zmqPort))

        while not stop_event.is_set():
            try:
                events = dict(await poller.poll(timeout=-1))
                if socket in events and events[socket] == zmq.POLLIN:
                    response = await socket.recv_multipart()
                    if len(response) == 2:
                        [topic, msg_packed] = response
                        if topic == b"flash":
                            msg_dict = msgpack.unpackb(msg_packed)
                            self.data_flash = dict2obj(msg_dict)
                            self.new_flash = True
                            socket.send_string("OK")
                        else:
                            socket.send_string("UNKNOWN")
                    else:
                        self.logger.log(
                            logging.ERROR, 'Flashlight zmqWorker malformed message')
                        socket.send_string("ERROR")

                if (self.new_flash):
                    self.dataReady.set()
                    self.new_flash  = False

            except:
                self.logger.log(logging.ERROR, 'Flashlight zmqWorker error')
                poller.unregister(socket)
                socket.close()
                socket = context.socket(zmq.REP)
                socket.bind("tcp://*:{}".format(self.zmqPort))
                poller.register(socket, zmq.POLLIN)
                self.new_neo = False

            await asyncio.sleep(0)

        self.logger.log(logging.DEBUG, 'Flashlight zmqWorker finished')
        socket.close()
        context.term()
        self.finished.set()

    def set_zmqPort(self, port):
        self.zmqPort = port

async def handle_termination(neo, logger, stop_events, tasks):
    '''
    Cancel slow tasks based on provided list (speed up closing of program)
    '''
    logger.log(logging.INFO, 'Controller ESC, Control-C or Kill signal detected')
    if tasks is not None: # This will terminate tasks faster
        logger.log(logging.INFO, 'Cancelling all Tasks...')
        for stop_event in stop_events:
            stop_event.set()
        neo.clear()
        await asyncio.sleep(1) # give some time for tasks to finish up
        for task in tasks:
            if task is not None:
                task.cancel()

##############################################################################################
# MAIN
##############################################################################################

async def main(args: argparse.Namespace):

    hum_stop_event = asyncio.Event()
    hum_stop_event.clear()

    zmq_stop_event = asyncio.Event()

    stop_events  = [hum_stop_event,  zmq_stop_event]

    # Setup logging
    logger = logging.getLogger(__name__)
    logger.log(logging.INFO, 'Starting Flashlight...')

    # Create the devices
    flash = FlashLight(logger=logger)
    zmq = zmqWorkerFlash(logger=logger, zmqPort=args.zmqport)

    flash.off()

    # Create all the async tasks
    # They will run until stop signal is created
    zmq_task  = asyncio.create_task(zmq.start(stop_event=zmq_stop_event))

    tasks = [zmq_task] # frequently updated tasks

    # Set up a Control-C handler to gracefully stop the program
    # This mechanism is only available in Unix
    if os.name == 'posix':
        # Get the main event loop
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT,  lambda: asyncio.create_task(handle_termination(neo=neo, logger=logger, tasks=tasks, stop_events=stop_events)) ) # control-c
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(handle_termination(neo=neo, logger=logger, tasks=tasks, stop_events=stop_events)) ) # kill

    # Main Loop for ZMQ messages,
    # Set lights according to ZMQ message we received

    while not zmq.finished.is_set():

        await zmq.dataReady.wait()
        zmq.dataReady.clear()

        if zmq.data_flash.state == flashstate["on"]:
            flash.on()

        elif zmq.data_flash.state == flashstate["off"]:
            flash.off()

        elif zmq.data_flash.state == flashstate["brightness"]:
            flash.brightness(zmq.data_flash.intensity)

        elif zmq.data_flash.state == flashstate["hum"]:
            hum_task = asyncio.create_task(flash.hum_start(stop_event=hum_stop_event))

        elif zmq.data_flash.state == flashstate["hum_stop"]:
            hum_stop_event.set()

        elif zmq.data_flash.state == flashstate["stop"]:
            # exit program
            for stop_event in stop_events: 
                stop_event.set()
            # Make sure lights are off
            flash.off()

    # Wait until all tasks are completed, which is when user wants to terminate the program
    await asyncio.wait(tasks, timeout=float('inf'))

    logger.log(logging.INFO,'Flashlight exit')

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help='sets the log level from info to debug',
        default = False
    )

    parser.add_argument(
        '-z',
        '--zmq',
        dest = 'zmqport',
        type = int,
        metavar='<zmqport>',
        help='port used by ZMQ, e.g. 5553 for \'tcp://*:5553\'',
        default = 5553
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        # format='%(asctime)-15s %(name)-8s %(levelname)s: %(message)s'
        format='%(asctime)-15s %(levelname)s: %(message)s'
    )

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        pass
