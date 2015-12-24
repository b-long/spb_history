#!/usr/bin/env python

# '{"force": true, "job_id": "RnaSeqSampleSizeData_20141016222857",
# "repository": "scratch",
#"bioc_version": "3.0",
# "svn_url": "https://tracker.bioconductor.org/file4746/RnaSeqSampleSizeData_0.99.0.tar.gz",
#"r_version": "3.1",
# "client_id": "single_package_builder_autobuild:1061:RnaSeqSampleSizeData_0.99.0.tar.gz",
# "time": "Thu Oct 16 2014 22:28:57 GMT-0700 (PST)"}'

import json
import sys
import datetime
from pytz import timezone
import stomp
import logging
# Modules created by Bioconductor
from bioconductor.config import BIOC_R_MAP
from bioconductor.config import BIOC_VERSION
from bioconductor.communication import getNewStompConnection
from bioconductor.config import TOPICS

logger = logging.getLogger()

if (len(sys.argv) != 3):
    logger.info("usage: %s <issue_id> <tracker_tarball_url>" % sys.argv[0])
    sys.exit(1)


# TODO: Name the callback for it's functionality, not usage.  This
# seems like it's as useful as 'myFunction' or 'myMethod'.  Why not
# describe capability provided ?
class MyListener(stomp.ConnectionListener):
    def on_connecting(self, host_and_port):
        logger.debug('on_connecting() %s %s.' % host_and_port)

    def on_connected(self, headers, body):
        logger.debug('on_connected() %s %s.' % (headers, body))

    def on_disconnected(self):
        logger.debug('on_disconnected().')

    def on_heartbeat_timeout(self):
        logger.debug('on_heartbeat_timeout().')

    def on_before_message(self, headers, body):
        logger.debug('on_before_message() %s %s.' % (headers, body))
        return headers, body

    def on_receipt(self, headers, body):
        logger.debug('on_receipt() %s %s.' % (headers, body))

    def on_send(self, frame):
        logger.debug('on_send() %s %s %s.' %
                      (frame.cmd, frame.headers, frame.body))
        logger.info("Receipt: %s" % frame.headers.get('receipt-id'))

    def on_heartbeat(self):
        logger.debug('on_heartbeat().')

    def on_error(self, headers, message):
        logger.debug('on_error(): "%s".' % message)

    def on_message(self, headers, body):
        logger.debug('on_message(): "%s".' % body)
        self.message_received = True

pacific = timezone("US/Pacific")
now0 = datetime.datetime.now()
tzname = pacific.tzname(now0)
if tzname == "PDT":
    offset = "0700"
else: # PST
    offset = "0800"

obj = {}
issue_id = sys.argv[1]
url = sys.argv[2]
segs = url.split("/")
pkgname = segs[4]
pkgname_bare = pkgname.split("_")[0]

obj['force']  = True
obj['bioc_version'] = BIOC_VERSION
obj['r_version'] = BIOC_R_MAP[BIOC_VERSION]
obj['svn_url'] = url
obj['repository'] = 'scratch'
now = pacific.localize(now0)
timestamp1 = now.strftime("%Y%m%d%H%M%S")
timestamp2 = now.strftime("%a %b %d %Y %H:%M:%S")
timestamp2 = timestamp2 + " GMT-%s (%s)" % (offset, tzname)
obj['job_id'] = "%s_%s" % (pkgname_bare, timestamp1)
obj['time'] = timestamp2
obj['client_id'] = "single_package_builder_autobuild:%s:%s" % (issue_id, pkgname)

json = json.dumps(obj)
logger.debug("Received JSON object: '%s'", json)

try:
    stomp = getNewStompConnection('', MyListener())
except:
    logger.info("Cannot connect")
    raise

this_frame = stomp.send(TOPICS['jobs'], json)
