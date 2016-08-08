import time
import logging

from stomp import ConnectionListener
from bioconductor.communication import getNewStompConnection


TIMEOUT = 60 # timeout in seconds

logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
logging.getLogger("stomp.py").setLevel(logging.WARNING)

class MyListener(ConnectionListener):
    def on_message(self, headers, message):
        logging.info(message)


try:
    logging.info("Attempting to connect using new communication module")
    stomp = getNewStompConnection('', MyListener())
    # stomp.set_listener('', PrintingListener())
    stomp.subscribe(destination="/topic/keepalive_response", id=1, ack='auto')
    logging.info("Connection established using new communication module")
except Exception as e:
    logging.error("main() Could not connect to ActiveMQ: %s." % e)
    raise


while True:
    stomp.send(destination="/topic/keepalive", body="stay alive!")
    # level is set to info to keep logs quiet, change to info if 
    # you want to see the following.
    logging.debug("Sent keepalive message.")
    time.sleep(TIMEOUT)

