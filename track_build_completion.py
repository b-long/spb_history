# This script listens to messages from the single
# package builder, and posts build reports to the
# issue tracker when it detects a completed build.

import sys
import json
import time
import tempfile
import os
import subprocess
import socket
import requests
import urllib.request, urllib.parse, urllib.error
import stomp
import uuid
import mechanize
import logging
import warnings
import re
from github import Github

# Modules created by Bioconductor
from bioconductor.communication import getNewStompConnection
from bioconductor.config import TOPICS
from bioconductor.config import ENVIR

logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)
logging.getLogger("stomp.py").setLevel(logging.DEBUG)

# set up django environment
from django.db import connection
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
django.setup()
path = os.path.abspath(os.path.dirname(sys.argv[0]))
segs = path.split("/")
segs.pop()
path =  "/".join(segs)
sys.path.append(path)
from viewhistory.models import Job
from viewhistory.models import Package
from viewhistory.models import Build
from viewhistory.models import Message


global build_counter
build_counter = {}

def handle_builder_event(obj):
    global build_counter
    if ("client_id" in obj and  \
        "single_package_builder" in obj['client_id']):
        builder_id = obj['builder_id']
        job_id = obj['job_id']

        if (not job_id in build_counter and obj['status'] == 'Got Build Request'):
            build_counter.setdefault(job_id, []).append(builder_id)
        elif (obj['status'] == 'Got Build Request' and \
                 not builder_id in build_counter[job_id]):
            build_counter.setdefault(job_id, []).append(builder_id)
        elif (job_id in build_counter and obj['status'] == 'autoexit'):
            logging.info("Looks like the build is complete on node %s" % \
            builder_id)
            build_counter.setdefault(job_id, []).remove(builder_id)

        if (job_id in build_counter and len(build_counter[job_id]) == 0):
            logging.info("We have enough finished builds to send a report.")
            handle_completed_build(obj)

def handle_completed_build(obj):

    logging.debug(obj)
    segs = obj['client_id'].split(":")
    roundup_issue = segs[1]
    tarball_name = segs[2]
    staging_url = ENVIR['spb_staging_url']
    f = urllib.request.urlopen("http://%s:8000/jid/%s" % (staging_url, obj['job_id']))
    job_id = f.read().strip()
    if job_id == "0":
        logging.info("There is no build report for this job!")
        return
    url = "http://%s:8000/job/%s/" % (staging_url, job_id.decode())
    logging.debug("build report url: %s\n" %url)
    sys.stdout.flush()
    logging.info("Sleeping for 30 seconds...\n")
    time.sleep(30)

    response = requests.get(url)
    html = response.text.encode('ascii', 'ignore')
    html = filter_html(html)
    logging.debug("myf: http://%s:8000/overall_build_status/%s" % (staging_url, job_id.decode()))
    f = urllib.request.urlopen("http://%s:8000/overall_build_status/%s"\
        % (staging_url, job_id.decode()))
    result = f.read().strip().decode().split(", ")
    url = copy_report_to_site(html, tarball_name)
    logging.debug("myurl: %s" % url)

    build_obj = Build.objects.filter(jid=obj['job_id'])

    post_text = get_post_text(result, url, tarball_name, build_obj)
    logging.debug("Printing Message: \n" + post_text)
    if "github" in segs[0]:
        post_to_github(roundup_issue, tarball_name, html, post_text,
            result)
    logging.info("Done.\n")
    sys.stdout.flush()

def get_post_text(build_result, url, package_name, build_obj):
    ok = True
    if not build_result[0] == "OK":
        ok = False
    problem = ", ".join(build_result)
    url2 = "https://contributions.bioconductor.org/git-version-control.html#new-package-workflow"

    msg = """
Dear Package contributor,

This is the automated single package builder at bioconductor.org.

Your package has been built on the Bioconductor Build System.

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
Please see the [build report][1] for more details.
"""
    msg2 = get_build_products_message(build_obj)
    if (not (msg2 == "")):
        msg = msg + """

The following are build products from R CMD build on the Bioconductor Build
System: \n %s
        """ % (msg2)
    else:
        msg = msg + """

The following are build products from R CMD build on the Bioconductor Build
System: \n ERROR before build products produced.
        """

    msg = msg + """

Links above active for 21 days.

<strong> Remember: </strong>if you submitted your package after July 7th, 2020,
when making changes to your repository push to
`git@git.bioconductor.org:packages/%s` to trigger a new build.
A quick tutorial for setting up remotes and pushing to upstream can be found [here][2].

[1]: %s
[2]: %s

    """ % (package_name, url, url2)
    return(msg)


def get_build_products_message(build_obj):
    msg = ""
    baseurl = "https://bioconductor.org/spb_reports/"
    for i in build_obj:
        os = i.os
        build_product = i.build_product
        if (not (build_product == "")):
            link_txt = "[" + build_product + "](" + baseurl + build_product + ")"
            msg = msg + os + ": " + link_txt + "\n"
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
    cmd = "/usr/bin/scp -i " + ENVIR['spb_RSA_key'] + \
          " %s webadmin@master.bioconductor.org:/extra/www/bioc/spb_reports/%s" % \
          (t[1], destfile)
    logging.info("cmd = %s\n" % cmd)
    subprocess.call(cmd, shell=True)
    chmod_cmd = "/usr/bin/ssh -i " + ENVIR['spb_RSA_key'] + \
                " webadmin@master.bioconductor.org \"chmod a+r /extra/www/bioc/spb_reports/%s\"" % destfile
    logging.info("chmod_cmd = %s\n" % chmod_cmd)
    subprocess.call(chmod_cmd, shell=True)
    os.remove(t[1])
    url = "http://bioconductor.org/spb_reports/%s" % destfile
    return(url)

def get_other_build_statuses(issue, besides):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        comments = issue.get_comments()
    comments = comments.reversed
    bot = "bioc-issue-bot"
    comments = [x for x in comments if x.user.login == bot]
    comments = [x for x in comments if x.body.strip().startswith("Dear Package contributor")]
    statuses = {}
    for comment in comments:
        url = list(filter(lambda x: "/spb_reports/" in x and "buildreport" in x, comment.body.split("\n")))[0]
        package = re.sub(r'_$', '', url.split("/")[-1].split("buildreport")[0])
        if package in statuses:
            break
        if package == besides:
            continue
        if "Congratulations!" in comment.body:
            statuses[package] = ["OK"]
        else:
            statline = list(filter(lambda x: "On one or more platforms" in x, comment.body.split("\n")))[0]
            statuses[package] = re.sub(r'"|\.$', '', statline.split("were:")[-1].strip()).split(', ')
    flat = [item for sublist in list(statuses.values()) for item in sublist]
    return (list(set(flat)))

def post_to_github(issue_number, package_name,
  html, post_text, build_results):
    issue_repos = ENVIR['github_issue_repo']
    token = ENVIR['github_token']
    gh = Github(login_or_token=token)
    repo = gh.get_repo(issue_repos)
    issue = repo.get_issue(number=int(issue_number))
    logging.info("Attempting to post to github at repos %s." % issue_repos)
    issue.create_comment(post_text)
    logging.info(build_results)
    if 'skipped' in build_results:
        build_results.remove('skipped')
    build_results = [br.replace("UNSUPPORTED", "OK") for br in build_results]
    possible_build_results = ['OK', 'WARNINGS', 'TIMEOUT', 'ERROR', 'ABNORMAL']
    labels = issue.get_labels()
    existing_labels = [i.name for i in labels]

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

    build_results = build_results + get_other_build_statuses(issue,  package_name)

    # and uniquify it:
    build_results = list(set(build_results))
    if 'skipped' in build_results:
        build_results.remove('skipped')
    build_results = [br.replace("UNSUPPORTED", "OK") for br in build_results]
    logging.debug("All build results: %s" % build_results)

    for res in possible_build_results:
        if res in build_results:
            if not res in existing_labels:
                issue.add_to_labels(res)
        else:
            if res in existing_labels:
                issue.remove_from_labels(res)

def filter_html(html):
    lines = html.decode().split("\n")
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

    def on_connected(self, frame):
        logging.debug('on_connected() %s %s.' % (frame.headers, frame.body))

    def on_disconnected(self):
        logging.debug('on_disconnected().')

    def on_heartbeat_timeout(self):
        logging.debug('on_heartbeat_timeout().')

    def on_before_message(self, frame):
        logging.debug('on_before_message() %s .' % frame)
        return frame

    def on_receipt(self, frame):
        logging.debug('on_receipt() %s %s.' % (frame.headers, frame.body))

    def on_send(self, frame):
        logging.debug('on_send() %s %s %s.' %
                      (frame.cmd, frame.headers, frame.body))

    def on_heartbeat(self):
        logging.info('on_heartbeat(): Waiting to do work.')

    def on_error(self, frame):
        logging.debug('on_error(): "%s".' % frame.message)

    def on_message(self, frame):
        headers = frame.headers
        body = frame.body
        logging.debug("Received stomp message: {message}".format(message=body))
        #logging.info("on_message() " + body)
        debug_msg = {
            "script": os.path.basename(__file__),
            "host": socket.gethostname()}
        dic = json.loads(body)
        msg = ''
        if 'builder_id' in dic:
            msg = msg + "builder_id: " + dic['builder_id'] + " "
        if 'job_id' in dic:
            msg = msg + "job_id: " + dic['job_id'] + " "
        if 'status' in dic:
            msg = msg + "status: " + dic['status'] + " "
            debug_msg['status'] = dic['status']
        if 'sequence' in dic:
            msg = msg + "sequence: " + str(dic['sequence']) + " "
        if 'elapsed_time' in dic:
            msg = msg + "elapsed_time: " + str(dic['elapsed_time']) + " "
        if 'retcode' in dic:
            msg = msg + "retcode: " + str(dic['retcode']) + " "
        if 'client_id' in dic:
            debug_msg['issue'] = dic['client_id']


        logging.info("on_message(): " + msg)


        # FIXME, don't hardcode keepalive topic name:
        if headers['destination'] == '/topic/keepalive':
            response = {
                "host": socket.gethostname(),
                "script": os.path.basename(__file__)
            }
            stomp.send(body=json.dumps(response),
                destination="/topic/keepalive_response")
            return()

# Already logged with archiver.py
# Activate this is debugging that archiver and track builds are in sync
#        stomp.send(body=json.dumps(debug_msg),
#            destination="/topic/keepalive_response")

        received_obj = None
        try:
            received_obj = json.loads(body)
        except ValueError as e:
            logging.error("Received invalid JSON: %s." % e)
            return
        finally:
            # Acknowledge that the message has been processed
            self.message_received = True

        try:
            # MTM FIXME: want to handle failure, but log traceback
            handle_builder_event(received_obj)
        except Exception as e:
            logging.error("failed to handle event: %s." % e)
            return



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
