
# This script listens to messages from the single
# package builder, and posts build reports to the
# issue tracker when it detects a completed build.


# FIXME - be aware that builds for different BioC versions
# may be occuring and we need to be aware of them and be able
# to tell them apart. Right now we're ignoring this.

import sys
import json
import time
import tempfile
import os
import subprocess
import socket
import requests
import urllib
import stomp
import uuid
import mechanize
import logging
import warnings
import re
from octokit import Octokit

from datetime import datetime

# Modules created by Bioconductor
from bioconductor.communication import getNewStompConnection
from bioconductor.config import BUILD_NODES
from bioconductor.config import TOPICS
from bioconductor.config import ENVIR

logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
logging.getLogger("stomp.py").setLevel(logging.WARNING)

global tracker_base_url
global build_counter
build_counter = {}
tracker_base_url = None

def handle_builder_event(obj):
    global build_counter
    if ("client_id" in obj and  \
        "single_package_builder" in obj['client_id'] \
        and 'status' in obj and obj['status'] == 'autoexit'):
        builder_id = obj['builder_id']
        job_id = obj['job_id']
        logging.info("Looks like the build is complete on node %s" % \
          builder_id)
        if (not job_id in build_counter):
            build_counter[job_id] = 1
        else:
            build_counter[job_id] += 1
        if (build_counter[job_id] == len(BUILD_NODES)):
            logging.info("We have enough finished builds to send a report.")
            handle_completed_build(obj)

def handle_completed_build(obj):
    global tracker_base_url
    if (obj.has_key('svn_url')):
        if 'tracker.bioconductor.org' in obj['svn_url']:
            tracker_base_url = "https://tracker.bioconductor.org"
        else:
            tracker_base_url = "http://tracker.fhcrc.org/roundup/bioc_submit"
    else:
        tracker_base_url = "http://tracker.fhcrc.org/roundup/bioc_submit"

    segs = obj['client_id'].split(":")
    roundup_issue = segs[1]
    tarball_name = segs[2]
    staging_url = ENVIR['spb.staging.url']
    f = urllib.urlopen("http://%s:8000/jid/%s" % (staging_url, obj['job_id']))
    job_id = f.read().strip()
    if job_id == "0":
        logging.info("There is no build report for this job!")
        return
    url = "http://%s:8000/job/%s/" % (staging_url, job_id)
    logging.info("build report url: %s\n" %url)
    sys.stdout.flush()
    logging.info("Sleeping for 30 seconds...\n")
    time.sleep(30)

    response = requests.get(url)
    html = response.text.encode('ascii', 'ignore')
    #logging.info("html before filtering: %s\n" % html)
    html = filter_html(html)
    #logging.info("html after filtering: %s\n" % html)

    f = urllib.urlopen("http://%s:8000/overall_build_status/%s"\
        % (staging_url, job_id))
    result = f.read().strip().split(", ")
    url = copy_report_to_site(html, tarball_name)
    post_text = get_post_text(result, url)
    if "github" in segs[0]:
        post_to_github(roundup_issue, tarball_name, html, post_text,
            result)
    else:
        post_to_tracker(roundup_issue, tarball_name, html, \
            post_text)
    logging.info("Done.\n")
    sys.stdout.flush()

def get_post_text(build_result, url):
    ok = True
    if not build_result[0] == "OK":
        ok = False
    problem = ", ".join(build_result)

    msg = """
Dear Package contributor,

This is the automated single package builder at bioconductor.org.

Your package has been built on Linux, Mac, and Windows.

    """
    if ok:
        msg = msg + """
Congratulations! The package built without errors or warnings
on all platforms.
        """
    else:
        msg = msg + """
On one or more platforms, the build results were: "%s".
This may mean there is a problem with the package that you need to fix.
Or it may mean that there is a problem with the build system itself.

        """ % problem
    msg = msg + """
Please see the following build report for more details:

%s

    """ % url
    return(msg)


def copy_report_to_site(html, tarball_name):
    #logging.info("HTML=\n\n%s\n\n" % html)
    t = tempfile.mkstemp()
    f = open(t[1], "w")
    #logging.info("temp filename is %s" % t[1])
    f.write(html)
    f.flush()
    f.close
    segs = tarball_name.split(".tar.gz")
    pkg = segs[0]
    now = time.localtime()
    ts = time.strftime("%Y%m%d%H%M%S", now)
    destfile = "%s_buildreport_%s.html" % (pkg, ts)
    cmd = \
      "/usr/bin/scp -i /home/biocadmin/.ssh/pkgbuild_rsa %s webadmin@master.bioconductor.org:/extra/www/bioc/spb_reports/%s" % \
      (t[1], destfile)
    logging.info("cmd = %s\n" % cmd)
    subprocess.call(cmd, shell=True)
    chmod_cmd = "/usr/bin/ssh -i /home/biocadmin/.ssh/pkgbuild_rsa webadmin@master.bioconductor.org \"chmod a+r /extra/www/bioc/spb_reports/%s\"" % destfile
    logging.info("chmod_cmd = %s\n" % chmod_cmd)
    subprocess.call(chmod_cmd, shell=True)
    os.remove(t[1])
    url = "http://bioconductor.org/spb_reports/%s" % destfile
    return(url)

def get_other_build_statuses(issue_number, hub, besides):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        comments = hub.repos("%s/issues/%s/comments" % (
            ENVIR['github_issue_repo']), issue_number)).get()
    comments.reverse()
    me = hub.user().get()['login']
    comments = filter(lambda x: x['user']['login'] == me, comments)
    comments = filter(lambda x: x['body'].strip().startswith("Dear Package contributor"),
      comments)
    statuses = {}
    for comment in comments:
        url = filter(lambda x: "/spb_reports/" in x, comment['body'].split("\n"))[0]
        package = re.sub(r'_$', '', url.split("/")[-1].split("buildreport")[0])
        if package in statuses:
            break
        if package == besides:
            continue
        if "Congratulations!" in comment['body']:
            statuses[package] = ["OK"]
        else:
            statline = filter(lambda x:
              x.startswith("On one or more platforms, the build results were"),
              comment['body'].split("\n"))[0]
            statuses[package] = re.sub(r'"|\.$', '',
              statline.split("were:")[-1].strip()).split(',')
    flat = [item for sublist in statuses.values() for item in sublist]
    return (list(set(flat)))

def post_to_github(issue_number, package_name,
  html, post_text, build_results):
    issue_repos = ENVIR['github_issue_repo']
    token = ENVIR['github_token']
    hub = Octokit(access_token=token)

    logging.info("Attempting to post to github at repos %s." % issue_repos)
    issue_url = "%s/issues/%s" % (issue_repos, issue_number)
    comments = hub.repos("%s/comments" % issue_url)
    res = comments.post({"body": post_text})
    logging.info("Post to github result: '{res}'".format(res = res))
    if 'skipped' in build_results:
        build_results.remove('skipped')
    labels = hub.repos("%s/labels" % issue_url).get()
    possible_build_results = ['OK', 'WARNINGS', 'TIMEOUT', 'ERROR', 'abnormal']
    existing_labels = [i['name'] for i in labels]

    # At this point we want to add one or more labels to the issue to
    # capture the results of this build. But if there is more than one
    # package in the issue, we don't want to remove the labels for
    # the builds of that issue. For example:
    # package A: build results: OK
    # package B: ERROR
    # overall build-related labels should be: OK, ERROR
    # So, build_results currently contains the results for the
    # just-concluded build. Let's combine it with earlier results from
    # other packages in this issue:
    build_results = build_results + get_other_build_statuses(issue_number, hub,
      package_name)
    # and uniquify it:
    build_results = list(set(build_results))

    for res in possible_build_results:
        if res in build_results:
            if not res in existing_labels:
                hub.repos("%s/labels" % issue_url).post([res])
        else:
            if res in existing_labels:
                hub.repos("%s/labels/%s" % (issue_url, res)).delete()



def post_to_tracker(roundup_issue, tarball_name, \
  html, post_text):
    global tracker_base_url
    username = ENVIR['tracker_user']
    password = ENVIR['tracker_pass']
    url = tracker_base_url

    logging.info("Attempting to post to tracker at url: '{url}'".format(url = url))

    br = mechanize.Browser()
    br.open(url)
    br.select_form(nr=2)
    br["__login_name"] = username
    br["__login_password"] = password
    res = br.submit()
    logging.info("Login to tracker result: '{res}'".format(res = res))

    url2 = url + "/issue%s" % roundup_issue

    br.open(url2)
    br.select_form(nr=2)
    #br['@action'] = 'edit'
    br['@note'] = post_text
    res2 = br.submit()
    logging.info("Post to tracker result: '{res}'".format(res = res2))

def filter_html(html):
    lines = html.split("\n")
    good_lines = []
    for line in lines:
        if ("InstallCommand" in line):
            segs = line.split("<pre")
            line = segs[0]
        if("pkgInstall(" in line):
            segs = line.split("</pre>")
            line = segs[1]
        if (not "staging" in line):
            good_lines.append(line)
    return("\n".join(good_lines))



# TODO: Name the callback for it's functionality, not usage.  This
# seems like it's as useful as 'myFunction' or 'myMethod'.  Why not
# describe capability provided ?
class MyListener(stomp.ConnectionListener):
    def on_connecting(self, host_and_port):
        logging.debug('on_connecting() %s %s.' % host_and_port)

    def on_connected(self, headers, body):
        logging.debug('on_connected() %s %s.' % (headers, body))

    def on_disconnected(self):
        logging.debug('on_disconnected().')

    def on_heartbeat_timeout(self):
        logging.debug('on_heartbeat_timeout().')

    def on_before_message(self, headers, body):
        logging.debug('on_before_message() %s %s.' % (headers, body))
        return headers, body

    def on_receipt(self, headers, body):
        logging.debug('on_receipt() %s %s.' % (headers, body))

    def on_send(self, frame):
        logging.debug('on_send() %s %s %s.' %
                      (frame.cmd, frame.headers, frame.body))

    def on_heartbeat(self):
        logging.info('on_heartbeat(): Waiting to do work.')

    def on_error(self, headers, message):
        logging.debug('on_error(): "%s".' % message)

    def on_message(self, headers, body):
        # FIXME, don't hardcode keepalive topic name:
        if headers['destination'] == '/topic/keepalive':
            logging.debug('got keepalive message')
            response = {"host": socket.gethostname(),
            "script": os.path.basename(__file__),
            "timestamp": datetime.now().isoformat()}
            stomp.send(body=json.dumps(response),
                destination="/topic/keepalive_response")

            return()

        debug_msg = {"script": os.path.basename(__file__),
            "host": socket.gethostname(), "timestamp":
            datetime.now().isoformat(), "message":
            "received message from %s, before thread" % headers['destination']}
        stomp.send(body=json.dumps(debug_msg),
            destination="/topic/keepalive_response")


        logging.info("Received stomp message: {message}".format(message=body))
        received_obj = None
        try:
            received_obj = json.loads(body)
        except ValueError as e:
            logging.error("Received invalid JSON: %s." % e)
            return

        handle_builder_event(received_obj)
        logging.info("Destination: %s" % headers.get('destination'))

        # Acknowledge that the message has been processed
        self.message_received = True


try:
    logging.debug("Attempting to connect using new communication module")
    stomp = getNewStompConnection('', MyListener())
    logging.info("Connection established using new communication module")
    stomp.subscribe(destination=TOPICS['events'], id=uuid.uuid4().hex,
                    ack='client')
    logging.info("Subscribed to destination %s" % TOPICS['events'])
    stomp.subscribe(destination="/topic/keepalive", id=uuid.uuid4().hex,
                    ack='auto')
    logging.info("Subscribed to  %s" % "/topic/keepalive")
except Exception as e:
    logging.error("main() Could not connect to ActiveMQ: %s." % e)
    raise

def main_loop():
    logging.info("Waiting to do work. ")
    while True:
        time.sleep(15)

if __name__ == "__main__":
    main_loop()
