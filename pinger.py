import stomp
import time
import logging

from bioconductor.communication import getNewStompConnection
from bioconductor.config import TOPICS


TIMEOUT = 60 # timeout in seconds

logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)
logging.getLogger("stomp.py").setLevel(logging.WARNING)


try:
    logging.debug("Attempting to connect using new communication module")
    stomp = getNewStompConnection('', stomp.PrintingListener())
    logging.info("Connection established using new communication module")
except Exception as e:
    logging.error("main() Could not connect to ActiveMQ: %s." % e)
    raise


while True:
    stomp.send(destination="/topic/keepalive", body="stay alive!")
    logging.debug("Sent keepalive message.")
    time.sleep(TIMEOUT)

