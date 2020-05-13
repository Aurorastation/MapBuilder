import os
import sys
import shutil
import subprocess
import glob
import hmac
import hashlib
import threading
import requests

import git
from git import Repo
import wget

from flask import Flask, send_from_directory, request

import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)

build_locks = {}

def get_dmmtools():
    if os.name == 'nt':
        return "dmm-tools.exe"
    else:
        return "dmm-tools"

def verify_hmac_hash(data, signature):
    secret = os.getenv('GITHUB_SECRET')
    if not secret:
        return False
    github_secret = bytes(secret, 'UTF-8')
    mac = hmac.new(github_secret, msg=data, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)

# @app.route('/')
# def ping():
#     # trueSecret = os.getenv('GITHUB_SECRET')
#     # if trueSecret and secret != trueSecret:
#     #     return 'Invalid SECRET'
#     th = threading.Thread(target=handle_generation, args=("Aurorastation/Aurora.3", "https://github.com/Aurorastation/Aurora.3.git"))
#     th.start()
#     return 'OK'

@app.route("/payload", methods=['POST'])
def github_payload():
    signature = request.headers.get('X-Hub-Signature')
    if not verify_hmac_hash(request.data, signature):
        return "Invalid HMAC", 500
    
    github_event = request.headers.get('X-GitHub-Event') 
    if not github_event == "push":
        return "Unsupported event: {}".format(github_event)
    
    payload = request.get_json()

    branch = payload["ref"] 
    if not branch == "refs/heads/master":
        return "Branch is not master: {} - No Build".format(branch)
    
    base_compare_url = payload["repository"]["compare_url"]
    base = payload["before"]
    head = payload["after"]
    compare_url = base_compare_url.replace("{base}",base).replace("{head}",head)
    
    response = requests.get(compare_url)
    data = response.json()
    for f in data["files"]:
        if f["filename"].startswith("maps/"):
            logger.debug("Queuing Build for: %s",f["filename"])
            th = threading.Thread(target=handle_generation, args=(payload["repository"]["full_name"], payload["repository"]["clone_url"], "master"))
            th.start()
            return 'Build Queued'
    logger.debug("No maps to build in branch")
    return 'No maps to build'

def handle_generation(fullname, remote, branch = None):
    logger.debug("Running Generation for. Fullname - {}, Remote - {}, Branch - {}".format(fullname, remote, branch))
    path = os.path.join(os.getcwd(), "__cache", fullname)
    if not path in build_locks:
        build_locks[path] = threading.Lock()
    with build_locks[path]:
        logger.debug("Started git update task for {}/{}.".format(remote, branch))
        repo = None
        if not os.path.isdir(path):
            logger.debug("Cloning Repo")
            repo = Repo.clone_from(remote, path)
        else:
            logger.debug("Updating Repo")
            repo = Repo(path)
            for remote in repo.remotes:
                remote.fetch()
            if branch:
                repo.git.checkout(branch)
                repo.remotes.origin.pull()
            else:
                repo.remotes.origin.pull()
        branchName = repo.active_branch.name
        logger.debug("Started map build task for {}/{}.".format(remote, branchName))
        maps = glob.glob(os.path.join(repo.working_tree_dir, "maps", "**", "*.dmm"))
        args = [os.path.abspath(get_dmmtools()), "minimap", "--disable", "icon-smoothing,fancy-layers"]
        for m in maps:
            a = []
            a.extend(args)
            a.append(m)
            subprocess.run(a, cwd=repo.working_tree_dir)
        logger.debug("Moving map builds for {}/{}.".format(remote, branchName))
        serveDir = os.path.join(os.getcwd(), "mapImages", fullname, branchName)
        if not os.path.isdir(serveDir):
            os.makedirs(serveDir, exist_ok=True)
        for f in glob.glob(os.path.join(serveDir, "*")):
            os.unlink(f)
        imageFiles = glob.glob(os.path.join(repo.working_tree_dir, "data", "minimaps", "*.png"))
        if len(imageFiles) != len(maps):
            logger.error("ALERT!!! Some map files failed to build. Built file count mismatches map file count.")
        for image in imageFiles:
            fn = os.path.basename(image)
            newPh = os.path.join(serveDir, fn)
            shutil.move(image, newPh)
        logger.debug("All done.")

# @app.route('/mapfile/<string:a>/<string:b>/<string:c>')
# def send_mapfile(a, b, c):
#     path = os.path.join(os.path.dirname(__file__), "__cache", a, b, "data", "minimaps")
#     return send_from_directory(path, c)

if __name__ == "__main__":
    secret = os.getenv('GITHUB_SECRET')
    if not secret:
        print("GITHUB_SECRET is not set. Aborting")
        sys.exit(1)
        
    logger.debug("Current secret is {}, use it while setting up webhook.".format(os.getenv('GITHUB_SECRET')))

    default_name = os.getenv("DEFAULT_NAME") or "Aurorastation/Aurora.3"
    default_remote =  os.getenv("DEFAULT_REMOTE") or "https://github.com/Aurorastation/Aurora.3.git"
    default_branch =  os.getenv("DEFAULT_BRANCH") or "master"
    # Check if we already have some images for the default repo:
    serveDir = os.path.join(os.getcwd(), "mapImages", default_name, default_branch)
    if not os.path.isdir(serveDir):
        logger.info("Map Images for {} - {} are not generated - Building".format(default_name, default_branch))
        handle_generation(default_name, default_remote, default_branch)
    if sum([len(files) for r, d, files in os.walk(serveDir)]) == 0:
        logger.info("Map Images for {} - {} are not generated - Building".format(default_name, default_branch))
        handle_generation(default_name, default_remote, default_branch)
  
    app.run(host='0.0.0.0')
