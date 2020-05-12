import os
import sys
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

import urllib.request

app = Flask(__name__)

build_locks = {}

def get_dmmtools():
    if os.name == 'nt':
        if not os.path.isfile("dmm-tools.exe"):
            wget.download("https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.4/dmm-tools.exe", "dmm-tools.exe")
        return "dmm-tools.exe"
    else:
        if not os.path.isfile("dmm-tools"):
            wget.download("https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.4/dmm-tools", "dmm-tools")
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
    data = request.data
    if verify_hmac_hash(data, signature):
        if request.headers.get('X-GitHub-Event') == "push":
            payload = request.get_json()
            
            if(payload["ref"] == "refs/heads/master"):
                
                response = requests.get(payload["compare"])
                data = response.json()
                for f in data["files"]:
                    if f["filename"].startswith("maps/"):
                        th = threading.Thread(target=handle_generation, args=(payload["repository"]["full_name"], payload["repository"]["clone_url"], "master"))
                        th.start()
                        break
                return 'OK'

def handle_generation(fullname, remote, branch = None):
    path = os.path.join(os.getcwd(), "__cache", fullname)
    if not path in build_locks:
        build_locks[path] = threading.Lock()
    with build_locks[path]:
        print("Started git update task for {}/{}.".format(remote, branch))
        repo = None
        if not os.path.isdir(path):
            repo = Repo.clone_from(remote, path)
        else:
            repo = Repo(path)
            for remote in repo.remotes:
                remote.fetch()
            if branch:
                repo.git.checkout(branch)
                repo.remotes.origin.pull()
            else:
                repo.remotes.origin.pull()
        branchName = repo.active_branch.name
        print("Started map build task for {}/{}.".format(remote, branchName))
        maps = glob.glob(os.path.join(repo.working_tree_dir, "maps", "**", "*.dmm"))
        args = [os.path.abspath(get_dmmtools()), "minimap", "--disable", "icon-smoothing,fancy-layers"]
        for m in maps:
            a = []
            a.extend(args)
            a.append(m)
            subprocess.run(a, cwd=repo.working_tree_dir)
        print("Moving map builds for {}/{}.".format(remote, branchName))
        serveDir = os.path.join(os.getcwd(), "mapImages", fullname, branchName)
        if not os.path.isdir(serveDir):
            os.makedirs(serveDir, exist_ok=True)
        for f in glob.glob(os.path.join(serveDir, "*")):
            os.unlink(f)
        imageFiles = glob.glob(os.path.join(repo.working_tree_dir, "data", "minimaps", "*.png"))
        if len(imageFiles) != len(maps):
            print("ALERT!!! Some map files failed to build. Built file count mismatches map file count.")
        for image in imageFiles:
            fn = os.path.basename(image)
            newPh = os.path.join(serveDir, fn)
            os.rename(image, newPh)
        print("All done.")

# @app.route('/mapfile/<string:a>/<string:b>/<string:c>')
# def send_mapfile(a, b, c):
#     path = os.path.join(os.path.dirname(__file__), "__cache", a, b, "data", "minimaps")
#     return send_from_directory(path, c)

if __name__ == "__main__":
    secret = os.getenv('GITHUB_SECRET')
    if not secret:
        print("GITHUB_SECRET is not set. Aborting")
        sys.exit(1)
        
    print("Current secret is {}, use it while setting up webhook.".format(os.getenv('GITHUB_SECRET')))
    app.run(host='0.0.0.0')
    # path = os.path.join(os.path.dirname(__file__), "__cache", "Aurorastation/Aurora.3")
    # handle_generation(path, "https://github.com/Aurorastation/Aurora.3.git", "")
