# -*- coding: utf8 -*-

from flask import Flask, request, Response
import hmac, hashlib, subprocess, os, sys, shutil,json
import logger, re
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
    if msg.strip() == '' and not err:
        return ''

    ret = identifier
    if err:
        ret = ret.replace("[+]", "[-]")
        ret += " (CRASHED):\n"
    else:
        ret += ":\n"
    ret += msg.strip()
    ret = ret.replace("\n", "\n    ")
    ret += "\n" if msg.strip() == '' else "\n\n"

    return ret





def downloadFromGit(repoName, force=False, branch="master", tag=None, webhook=True):
    LOGGER.debug("starting git operations for "+branch+"@"+ repoName +"...")

    error = False
    if branch == "master":
        repoPath = GITPATH + repoName + "/"
    else:
        repoPath = GITPATH + repoName + "-" + branch + "/"

    output = ""


    # evaluate CONFIG
    stop = False
    releaseOnly = False

    if CONFIG and CONFIG.get(repoName):
        repoConfig = CONFIG[repoName]

        # white/blacklists
        whitelist = repoConfig.get("whitelistedBranches")
        blacklist = repoConfig.get("blacklistedBranches")
        if whitelist and len(list(filter(lambda x: re.compile(x).match(branch), whitelist))) == 0:
            stop = True
        if blacklist and len(list(filter(lambda x: re.compile(x).match(branch), blacklist))) > 0:
            stop = True

        # releasesOnly
        if repoConfig.get("releasesOnly"):
            releasesOnlyConfig = repoConfig["releasesOnly"]
            if type(releasesOnlyConfig) == bool:
                releaseOnly = releasesOnlyConfig
            elif type(releasesOnlyConfig) == dict and branch in releasesOnlyConfig:
                releaseOnly = releasesOnlyConfig[branch]

    # react on config file
    if stop or os.path.exists(repoPath + "disabled") or os.path.exists(repoPath + "disabled-" + branch):
        if not force:
            if stop:
                return Response("Auto deployment for branch ('"+ branch +"') in config disabled, add query param 'force=1' to deploy anyway.", content_type=contenttype)
            else:
                return Response("Auto deployment for branch ('" + branch + "') per file disabled, add query param 'force=1' to deploy anyway.", content_type=contenttype)
        else:
            if stop:
                output += "[!] Auto deployment for branch ('"+ branch +"') in config disabled, ignoring this and deploy anyway...\n\n"
            else:
                output += "[!] Auto deployment for branch ('" + branch + "') per file disabled, ignoring this and deploy anyway...\n\n"


    ignoreReleaseFlag = request.args.get("ignoreRelease")
    ignoreReleaseFlag = True if ignoreReleaseFlag and ignoreReleaseFlag != "0" else False

    # current event is no release
    if releaseOnly and not tag:
        if not ignoreReleaseFlag:
            return Response("This branch '"+branch+"' should only autodeploy releases!\n" +
                            "Add query param 'ignoreRelease=1' to deploy anyway.", content_type=contenttype)
        else:
            output += "[!] Auto deployment for branch ('"+ branch +"') only enabled for releases. Ignoring this and deploy anyway...\n\n"



    # current event is release, check if it is the newest
    # check for this case after pull/clone!


    firstSetup = False
    # deploy
    if not os.path.exists(repoPath):
        # clone git repo
        try:
            os.makedirs(repoPath, exist_ok=True)
        except:
            pass

        args = ["git", "clone", "-b", branch, GITBASEURL + repoName + ".git", "."]
        gitOut, gitError = call(args, cwd=repoPath)
        output += addOutput("[+] " + " ".join(args), gitOut, gitError)
        error |= gitError

        if gitError:
            shutil.rmtree(repoPath, True)

        firstSetup = True
    else:
        # pull from repo
        cmd = ["git", "clean", "-d", "-f"]
        gitOut, gitError = call(cmd, cwd=repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "reset", "--hard"]
        gitOut, gitError = call(cmd, cwd=repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "checkout", branch]
        gitOut, gitError = call(cmd, cwd=repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "fetch"]
        gitOut, gitError = call(cmd, cwd=repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "reset", "--hard", "origin/" + branch]
        gitOut, gitError = call(cmd, cwd=repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError



    # check for newest release
    if tag:
        # get all tags
        gitOut, gitError = call(["git", "tag", "--sort=-committerdate"], cwd=repoPath)

        if gitError:
            output += addOutput("[+] git tag --sort=-committerdate", gitOut, gitError)
            error |= gitError

        gitOut = gitOut.strip()
        releases = gitOut.splitlines()
        releasesAnnotated = list(map(lambda x: x.strip(), releases[:]))

        if tag == "latest":
            if len(releases) > 0:
                tag = releases[0]
                output += "[+] switch to latest release ('" + tag +"') on ('"+branch+"')\n\n"
            else:
                output = "ATTENTION!\nNo release available, switch to latest push.\n\n\n===========================\n" + output
                tag = None

        # tag exists
        if tag in releases:
            releaseNumber = releases.index(tag)
            releasesAnnotated[releaseNumber] = "%s <= specified release" % releasesAnnotated[releaseNumber]

            if releaseNumber > 0 and not ignoreReleaseFlag and not webhook:
                # not the newest release (manual deploy only)
                temp = "ATTENTION!\n"
                temp += ("Specified release ('%s') is not the newest on this branch. Will set release to the newest one ('%s').\n" +
                           "If you want to checkout your release anyway, add query param 'ignoreRelease=1' to URL.\n") % (tag, releases[0])
                temp += ("History of releases (newest top, oldest bottom):\n" +
                         "%s\n\n") % '\n'.join(map(lambda x: "  %s" % x, releasesAnnotated))
                temp += "If you want to silence this warning, specify the latest release or set the release name to 'latest'\n"+\
                        "to always deploy the latest release.\n\n\n"

                output = temp + "===========================\n" + output

                tag = releases[0]

            elif ignoreReleaseFlag and not webhook:
                # ignore newest release (manual deploy only)
                output += ("[!] Specified release ('%s') is not the newest on this branch.\n" +
                           "    Ignoring this and checkout this release anyway.\n\n") % releases[0]

            elif webhook and not releaseOnly:
                # auto deploy only and releaseOnly disabled branch
                temp = "ATTENTION!\nreleaseOnly Mode for ('" + branch + "') disabled.\n" + \
                       "Release webhook invocation only restores latest push.\n\n\n===========================\n"
                output = temp + output
                tag = None

            elif webhook and releaseOnly and releaseNumber > 0:
                # auto deploy only and releaseOnly branch
                temp = "ATTENTION!\nreleaseOnly Mode for ('" + branch + "') enabled.\n" + \
                       "Specified release is not the newest release. Release webhook invocation only pulls latest release.\n\n\n===========================\n"
                output = temp + output
                tag = releases[0]


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
            setupOut, setupErr = call([repoPath + "setup", branch, request.headers["Host"]])
            output += addOutput("[+] Setup Script", setupOut, setupErr)
            error |= gitError
        else:
            output += "[!] no setup script found\n\n"
    elif not error:
        # launch reload script
        if os.path.exists(repoPath + "reload"):
            relOut, relErr = call([repoPath + "reload", branch, request.headers["Host"]])
            output += addOutput("[+] reload script", relOut, relErr)
            error |= relErr
        else:
            output += "[!] no reload script found\n\n"
    elif error:
        output += "[!] skip reload or setup script (deploying failed)\n\n"

    output = output.strip()

    # webserver response
    if error:
        output = "Automatic deploy failed!\n========================\n".upper() + output
        return requestError(output, code=500)

    else:
        return Response(output + "\n\nOverall success!", content_type=contenttype)






@app.route('/github', methods=["GET", "POST"])
def github():
    headers = request.headers
    jsonData = request.get_json(silent=True)

    if DEBUG:
        # check local HMAC calculation
        headers = {
            "User-Agent": "GitHub-Hookshot/a837270",
            "X-GitHub-Delivery": "0aa67100-1b16-11e7-8bbf-ee052e733e39",
            "X-GitHub-Event": "push",
            "X-Hub-Signature": "sha1=c6498e16d2fa649cb8d92bea4c2a7f1dabfb7643"
        }
        rawData = open("/Users/Philipp/Desktop/Scripts/Deployer/payload_github_push.json", "rb").read()
        jsonData = json.loads(rawData.decode())
    else:
        rawData = request.get_data(as_text=False)

    if not jsonData:
        LOGGER.warning("No json data in request!")
        return requestError()

    if "X-GitHub-Delivery" not in headers or "X-GitHub-Event" not in headers or "X-Hub-Signature" not in headers or "GitHub-Hookshot" not in headers["User-Agent"]:
        LOGGER.warning("Unsupported Header combination:\n" + "\n".join(map(lambda x: "    \"%s\": \"%s\"" %(x[0], x[1]), headers.items())))
        return requestError()


    # calculate HMAC
    if CONFIG["hmacSecret"]:
        secret = CONFIG["hmacSecret"]
        mac = hmac.new(secret, rawData, hashlib.sha1).hexdigest()

        if "sha1=" + mac != headers["X-Hub-Signature"]:
            LOGGER.critical("Invalid GitHub signature, automatic deploy failed!")
            LOGGER.debug("Computed Mac: sha1=" + mac + "\n" +
                         "Sent Mac    : " + headers["X-Hub-Signature"])
            LOGGER.debug("type(data) = " + str(type(rawData)) + "\nPayload:\n" + rawData.decode())
            return requestError("Invalid Signature 401", 401)
    else:
        LOGGER.warning("Skip signature validation!")


    # setup git operation
    repoName = jsonData["repository"]["name"]
    tag = None

    if headers["X-GitHub-Event"] == "push":
        if "refs/heads" not in jsonData["ref"]:
            LOGGER.debug("No branch push detected, ignore push event.")
            return Response("No branch push detected, ignore push event", content_type=contenttype)

        branch = jsonData["ref"].replace("refs/heads/", "")

    elif headers["X-GitHub-Event"] == "release":
        branch = jsonData["release"]["target_commitish"]
        tag = jsonData["release"]["tag_name"]

    else:
        LOGGER.critical("Received an unsupported GitHub Event: "  + headers["X-GitHub-Event"])
        return requestError("Received an unsupported GitHub Event", code=405)


    # run operation
    resp = downloadFromGit(repoName, branch=str(branch), tag=tag)
    if resp.status_code >= 400:
        LOGGER.critical(resp.get_data(as_text=True).strip())
    else:
        LOGGER.debug(resp.get_data(as_text=True).strip())
    return resp





@app.route('/deploy/<repoName>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>/<tag>', methods=["GET", "POST"])
def deploy(repoName, branch="master", tag=None):
    if request.method == "GET":
        return Response('<form method="POST"><input id="button" type="submit" value="Start"></form><script>document.getElementById("button").focus();</script>')

    force = True if request.args.get("force") and request.args.get("force") != "0" else False

    resp = downloadFromGit(repoName, force=force, branch=branch, tag=tag, webhook=False)
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

    cmd = "which python"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    cmd = "which python3"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    output += "[+] current sys.path:\n" + "\n".join(map(lambda x: "    %s" % x, sys.path)) + "\n\n"

    output += "[+] Request-Headers:\n    {\n" + "\n".join(map(lambda x: "       \"%s\": \"%s\"" %(x[0], x[1]), request.headers.items())) + "\n    }\n\n"

    cmd = "env"
    gitOut, gitError = call(cmd, shell=True)
    output += addOutput("[+] " + cmd, gitOut, gitError)

    return Response(output, content_type=contenttype)


if __name__ == '__main__':
    app.run(debug=DEBUG)
