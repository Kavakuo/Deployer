# -*- coding: utf8 -*-

from flask import Flask, request, Response
import hmac, hashlib, subprocess, os, sys, shutil,json
import logger
from copy import copy

try:
    from config import CONFIG
except:
    CONFIG = None
    print("CONFIG missing!")
    sys.exit(1)


# validate CONFIG
if "deployPath" not in CONFIG or "gitBaseUrl" not in CONFIG:
    print("Invalid config.py, check sample!")
    sys.exit(1)

DEBUG = False
GITPATH = CONFIG["deployPath"]
GITBASEURL = CONFIG["gitBaseUrl"]
if os.path.exists("/Users/Philipp/"):
    GITPATH = "/Users/Philipp/"
    DEBUG = True


# Formatter for WatchedFileHandler
class CustomFormatter(logger.logging.Formatter):
    def __init__(self, fmt="%s %s in %s():%s:\n%s" %(logger.LOG_FMT_TIME, logger.LOG_FMT_LEVEL, logger.LOG_FMT_FUNC_NAME, logger.LOG_FMT_LINE, logger.LOG_FMT_MESSEGE), datefmt="%Y-%m-%d %H:%M:%S"):
        super(CustomFormatter, self).__init__(fmt, datefmt)

    def format(self, record):
        record = copy(record)
        res = super().format(record)
        res = res.strip()
        # shift linebreaks of the same log to the right
        res = res.replace("\n", "\n\t")
        return res



logPath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "log.log")
flaskLogPath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "FlaskLog.log")

LOGGER = logger.loggerWithName("Deployment")
LOGGER.addHandler(logger.configureHandler(logger.WatchedFileHandler(logPath, encoding="utf-8"), CustomFormatter()))
LOGGER.addHandler(logger.configureHandler(logger.StreamHandler(sys.stdout), logger.logging.Formatter()))
LOGGER.setLevel(logger.logging.DEBUG)

if not DEBUG and "mailLogger" in CONFIG:
    LOGGER.addHandler(logger.configureHandler(CONFIG["mailLogger"], logger.PNMailLogFormatter(), logLevel=logger.logging.CRITICAL))


app = Flask(__name__)
app.logger.addHandler(logger.configureHandler(logger.WatchedFileHandler(flaskLogPath), logger.PNLogFormatter()))
app.logger.setLevel(logger.logging.DEBUG)

contenttype = "text/plain; charset=utf-8"

if not os.path.exists(GITPATH):
    try:
        os.makedirs(GITPATH, exist_ok=True)
    except:
        pass


def requestError(message="Error 400", code=400):
    return Response(message, status=code, content_type=contenttype)

def call(args, **kwargs):
    error = False
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT, **kwargs).decode()
    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        # log crashed command
        cmd = " ".join(args) if type(args) == list else args

        outputlog = addOutput('[+] "' + cmd + '" crashed with output',output,True)
        LOGGER.warning(outputlog)
        error = True

    return output, error


def addOutput(identifier, msg, err):
    ret = identifier
    if err:
        ret = ret.replace("[+]", "[-]")
        ret += " (CRASHED):\n"
    else:
        ret += ":\n"
    ret += msg.strip()
    ret = ret.replace("\n", "\n    ")
    ret += "\n\n"
    return ret


def downloadFromGit(repoName, force=False, branch="master", tag=None):
    LOGGER.debug("starting git operations for "+branch+"@"+ repoName +"...")

    error = False
    if branch == "master":
        repoPath = GITPATH + repoName + "/"
    else:
        repoPath = GITPATH + repoName + "-" + branch + "/"

    output = ""


    # evaluate CONFIG
    stop = False
    if CONFIG and CONFIG.get(repoName):
        whitelist = CONFIG[repoName].get("whitelistedBranches")
        blacklist = CONFIG[repoName].get("blacklistedBranches")
        if whitelist and branch not in whitelist:
            stop = True
        if blacklist and branch in blacklist:
            stop = True

    # react on config file
    if stop:
        if not force:
            return Response("Auto deployment for Branch '"+ branch +"' in config disabled, add query param \"force=1\" to overwrite this.", content_type=contenttype)
        else:
            output += "[!] Auto deployment for "+ branch +" in config disabled, ignoring this.\n\n"



    firstSetup = False

    # deploy
    if not os.path.exists(repoPath):
        # clone git repo
        try:
            os.makedirs(repoPath)
        except:
            pass

        gitOut, gitError = call(["git", "clone", "-b", branch, GITBASEURL + repoName + ".git", "."], cwd=repoPath)
        output += addOutput("[+] git clone -b " + branch + GITBASEURL + repoName + ".git .", gitOut, gitError)
        error |= gitError

        if gitError:
            shutil.rmtree(repoPath, True)


        firstSetup = True
    else:
        # pull from repo
        if os.path.exists(repoPath + "disabled") or os.path.exists(repoPath + "disabled-" + branch):
            if not force:
                return Response("Auto deployment disabled, add query param \"force=1\" to overwrite this.",content_type=contenttype)
            else:
                output = "(Auto deployment disabled)\n"

        cmd = "git clean -d -f && git reset --hard && git checkout "+ branch +" && git pull --rebase"
        gitOut, gitError = call(cmd, cwd=repoPath, shell=True)
        output += addOutput("[+] " + cmd, gitOut, gitError)
        error |= gitError


    # checkout tag
    if tag and os.path.exists(repoPath):
        verOut, verErr = call("git checkout " + str(tag), cwd=repoPath, shell=True)
        output += addOutput("[+] git checkout " + str(tag), verOut, verErr)
        error |= verErr
    elif not os.path.exists(repoPath) and tag:
        output += "[!] skip checkout version\n\n"


    # scripts
    if firstSetup and not error:
        # launch setup script
        if os.path.exists(repoPath + "setup"):
            setupOut, setupErr = call([repoPath + "setup", branch])
            output += addOutput("[+] Setup Script", setupOut, setupErr)
            error |= gitError
        else:
            output += "[!] no setup script found\n\n"
    elif not error:
        # launch reload script
        if os.path.exists(repoPath + "reload"):
            relOut, relErr = call([repoPath + "reload", branch])
            output += addOutput("[+] reload script", relOut, relErr)
            error |= relErr
        else:
            output += "[!] no reload script found\n\n"
    elif error:
        output += "[!] skip reload or setup script (deploying failed)\n\n"

    output = output.strip()

    # webserver response
    if error:
        output = "Automatic deploy failed!\n------------------------\n" + output
        return requestError(output, code=500)

    else:
        return Response(output + "\n\nOverall success!", content_type=contenttype)


@app.route('/github', methods=["GET", "POST"])
def github():
    headers = request.headers
    jsonData = request.get_json(silent=True)

    if DEBUG:
        headers = {
            "User-Agent": "GitHub-Hookshot/a837270",
            "X-GitHub-Delivery": "0aa67100-1b16-11e7-8bbf-ee052e733e39",
            "X-GitHub-Event": "push",
            "X-Hub-Signature": "sha1=c6498e16d2fa649cb8d92bea4c2a7f1dabfb7643"
        }
        rawData = open("/Users/Philipp/Desktop/Scripts/Deployer/payload_github_push.json", "rb").read()
        jsonData = json.loads(rawData.decode())


    if not jsonData:
        LOGGER.warning("No json data in request!")
        return requestError()

    if "X-GitHub-Delivery" not in headers or "X-GitHub-Event" not in headers or "X-Hub-Signature" not in headers or "GitHub-Hookshot" not in headers["User-Agent"]:
        LOGGER.warning("Unsupported Header combinaion:\n" + str(headers))
        return requestError()


    # calculate HMAC

    if CONFIG["hmacSecret"]:
        data = request.get_data(as_text=False) if not DEBUG else rawData
        secret = CONFIG["hmacSecret"]
        mac = hmac.new(secret, data, hashlib.sha1).hexdigest()

        if "sha1=" + mac != headers["X-Hub-Signature"]:
            LOGGER.critical("Invalid GitHub signature, automatic deploy failed!")
            LOGGER.debug("Computed Mac: sha1=" + mac + "\n" +
                         "Sent Mac    : " + headers["X-Hub-Signature"])
            LOGGER.debug("type(data) = " + str(type(data)) + "\nPayload:\n" + data.decode())
            return requestError("Invalid Signature 401", 401)
    else:
        LOGGER.warning("Skip signature validation!")

    # setup git operation
    repoName = jsonData["repository"]["name"]

    if headers["X-GitHub-Event"] == "push":
        branch = jsonData["ref"].replace("refs/heads/", "")

        # run operation
        resp = downloadFromGit(repoName, branch=str(branch))
        if resp.status_code >= 400:
            LOGGER.critical(resp.get_data(as_text=True).strip())
        else:
            LOGGER.debug(resp.get_data(as_text=True).strip())
        return resp

    else:
        LOGGER.critical("Received an unsupported GitHub Event: "  + headers["X-GitHub-Event"])
        return requestError("Unsupported Github Event", code=405)



@app.route('/deploy/<repoName>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>/<tag>', methods=["GET", "POST"])
def deploy(repoName, branch="master", tag=None):
    if request.method == "GET":
        return Response('<form method="POST"><input id="button" type="submit" value="Start"></form><script>document.getElementById("button").focus();</script>')

    force = request.args.get("force")
    if force:
        force = bool(int(force))

    resp = downloadFromGit(repoName, force=force, branch=str(branch), tag=tag)
    if resp.status_code >= 400:
        LOGGER.warning(resp.get_data(as_text=True).strip())
    else:
        LOGGER.debug(resp.get_data(as_text=True).strip())

    return resp


@app.route('/info', methods=["GET"])
def info():
    output = ""
    cmd = "which git"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "git --version"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "whoami"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "git config --global -l"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "env"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "env"
    gitOut, gitError = call(cmd, shell=True, env=os.environ.copy())
    output += addOutput("[+] with explicit env " + cmd, gitOut, gitError)

    output += "os.environ:\n" + str(os.environ.copy())

    return Response(output, content_type=contenttype)


if __name__ == '__main__':
    app.run(debug=DEBUG)
