# Flashlight
Raspi PWM is attached to the Meanwell constant current LED driver control signal.
On, Off, Humming is sent via ZMQ to service program to execute the functions.

## PWM on Raspberry Pi
There are two independent PWM controllers. I2S is using one of them.
There is soft and hard ware PWM where hardware PWM uses DMA to set the singals.
Software PWM works on all GPIO pins.

Hardware PWM works on:
- PWM0 GPIO12 and GPIO18
- PWM1 GPIO13 and APGIO19

Neopixel is usually attached to GPIO18, using I2S is not possible when using hardware PWM or NEOPIXEL. 
