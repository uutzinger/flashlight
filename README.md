# Flashlight
An async server to control PWM pin for Flashlight intensity control.

Raspi PWM is attached to the Meanwell constant current LED driver control signal.
Supports
- On / Off, 
- Humming
- Intensity

Request are sent via ZMQ to this server to execute the functions.

## PWM on Raspberry Pi
There is soft and hard ware PWM where hardware PWM uses DMA to set the singals.

There are two independent hardware PWM controllers. I2S is using one of them.
Software PWM works on all GPIO pins.

Hardware PWM works on:
- PWM0 GPIO12 and GPIO18
- PWM1 GPIO13 and APGIO19

Neopixel is usually attached to GPIO18, using I2S is not possible when using hardware PWM or NEOPIXEL. 
