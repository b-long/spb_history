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
import re
# Modules created by Bioconductor
from bioconductor.config import BIOC_R_MAP
from bioconductor.config import BIOC_VERSION
from bioconductor.communication import getNewStompConnection
from bioconductor.config import TOPICS

logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)

if (len(sys.argv) != 3):
    logging.info("usage: %s <github/tracker issue id> <github repos url/tracker tarball url>" % sys.argv[0])
    sys.exit(1)



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
if "tracker.bioconductor.org" in url.lower():
    pkgsrc = "autobuild"
    segs = url.split("/")
    pkgname = segs[4]
    pkgname_bare = pkgname.split("_")[0]
elif "https://github.com" in url.lower():
    pkgsrc = "github"
    urlcopy = re.sub(r'\.git$', "", url)
    urlcopy = re.sub(r'\/$', "", urlcopy)
    segs = urlcopy.split("/")
    pkgname = segs[len(segs)-1]
    pkgname_bare = pkgname

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
obj['client_id'] = "single_package_builder_%s:%s:%s" % (pkgsrc, issue_id, pkgname)

json = json.dumps(obj)
logging.debug("Received JSON object: '%s'", json)

try:
    stomp = getNewStompConnection('', stomp.PrintingListener())
except:
    logging.info("Cannot connect")
    raise

this_frame = stomp.send(TOPICS['jobs'], json)
