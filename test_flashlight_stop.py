##########################################################
# Flashlight STOP
#
# Urs Utzinger, Spring 2023
###########################################################
import zmq
import msgpack
import logging
import argparse

from flashlight import flashData, flashstate, obj2dict

##############################################################################################
# MAIN
##############################################################################################

if __name__ == '__main__':

    # Setup logging
    logger = logging.getLogger(__name__)

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
        type = str,
        metavar='<zmqport>',
        help='port used by ZMQ, e.g. \'tcp://10.0.0.2:5553\'',
        default = 'tcp://localhost:5553'
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        # format='%(asctime)-15s %(name)-8s %(levelname)s: %(message)s'
        format='%(asctime)-15s %(levelname)s: %(message)s'
    )

    logger.log(logging.INFO, 'Stopping flashlight program')

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(args.zmqport)
    data_flash  = flashData(state=flashstate["stop"])
    flash_msgpack = msgpack.packb(obj2dict(vars(data_flash)))
    socket.send_multipart([b"light", flash_msgpack])

    # response = socket.recv_string()

    logger.log(logging.INFO, 'Done')
