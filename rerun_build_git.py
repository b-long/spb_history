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

if (len(sys.argv) != 4):
    logging.info("usage: %s <github issue id/package name> <git.bioconductor.org url / github repos url> <newpackage true/false>" % sys.argv[0])
    sys.exit(1)



eastern = timezone("US/Eastern")
now0 = datetime.datetime.now()
tzname = eastern.tzname(now0)
if tzname == "EDT":
    offset = "0400"
else: # EST
    offset = "0500"

obj = {}
issue_id = sys.argv[1]
url = sys.argv[2]
newpackage = sys.argv[3]

if "https://git.bioconductor.org" in url.lower():
    pkgsrc = "bioconductor"
    segs = url.split("/")
    pkgname = segs[len(segs)-1]
    pkgname_bare = pkgname
elif "https://github.com" in url.lower():
    pkgsrc = "github"
    urlcopy = re.sub(r'\.git$', "", url)
    urlcopy = re.sub(r'\/$', "", urlcopy)
    segs = urlcopy.split("/")
    pkgname = segs[len(segs)-1]
    pkgname_bare = pkgname

# pkgsrc will control posting to github
if newpackage:
    pkgsrc = "github"


if url.endswith(".git"):
    url = url.replace(".git", "")


obj['force']  = True
obj['bioc_version'] = BIOC_VERSION
obj['r_version'] = BIOC_R_MAP[BIOC_VERSION]
obj['svn_url'] = url
obj['repository'] = 'scratch'
now = eastern.localize(now0)
timestamp1 = now.strftime("%Y%m%d%H%M%S")
timestamp2 = now.strftime("%a %b %d %Y %H:%M:%S")
timestamp2 = timestamp2 + " GMT-%s (%s)" % (offset, tzname)
obj['job_id'] = "%s_%s" % (pkgname_bare, timestamp1)
obj['time'] = timestamp2
obj['client_id'] = "single_package_builder_%s:%s:%s" % (pkgsrc, issue_id, pkgname)
obj['newpackage'] = newpackage

json = json.dumps(obj)
logging.debug("Received JSON object: '%s'", json)

try:
    stomp = getNewStompConnection('', stomp.PrintingListener())
except:
    logging.info("Cannot connect")
    raise

this_frame = stomp.send(TOPICS['jobs'], json)
