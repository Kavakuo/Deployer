# coding=utf-8

from flask import Flask, request, Response
import hmac, hashlib, os, sys, shutil, json, re
from utils import logger
from classes import DeployInfo, APISettings, Release, TEST_SEQs
from context import CONTEXT
from functions import call, addOutput
from functools import wraps


flaskLogPath = os.path.join(CONTEXT.PROJECT_FOLDER, "Logs", "FlaskLog.log")
app = Flask(__name__)
app.logger.addHandler(logger.configureHandler(logger.WatchedFileHandler(flaskLogPath), logger.PNLogFormatter()))
app.logger.setLevel(logger.logging.DEBUG)


contenttype = "text/plain; charset=utf-8"

LOGGER = CONTEXT.LOGGER


def requestError(message="Bad Request 400", code=400):
    return Response(message, status=code, content_type=contenttype)


def logErrorRespToLevel(resp, level):
    if resp.status_code >= 400:
        if type(level) == int:
            CONTEXT.LOGGER.log(level, resp.get_data(as_text=True).strip())
        else:
            level(resp.get_data(as_text=True).strip())
    else:
        CONTEXT.LOGGER.debug(resp.get_data(as_text=True).strip())
    
    return resp



def downloadFromGit(repoName, settings, branch="master", tag=None, webhook=False, release=None):
    if not release:
        release = Release(settings)

    if not settings.deployPossible():
        return requestError("Invalid Config.py file! Take a look at the sample.", code=500)

    LOGGER.debug("starting git operations for " + branch + "@"+ repoName +"...")
    output = ""

    force = True if request.args.get("force") and request.args.get("force") != "0" else False
    ignoreTagDate = True if request.args.get("ignoreTagDate") and request.args.get("ignoreTagDate") != "0" else False
    ignoreTag = True if request.args.get("ignoreTag") and request.args.get("ignoreTag") != "0" else False
    ignoreRelease = True if request.args.get("ignoreRelease") and request.args.get("ignoreRelease") != "0" else False
    
    
    if webhook and (force or ignoreRelease or ignoreTagDate):
        output += "Query parameters to overwrite certain behaviours are not supported when using webhooks!"
        CONTEXT.addTestSeq(TEST_SEQs.dl_whQueryNotAllowed)
        return requestError(output)

    error = False
    deployInfo = DeployInfo(settings, repoName, branch)
    

    # evaluate CONFIG
    stop = False
    releaseOnly = False
    tagsOnly = False

    repoConfig = None
    if CONTEXT.CONFIG and CONTEXT.CONFIG.get(repoName):
        repoConfig = CONTEXT.CONFIG[repoName]

    if not repoConfig and release.isRelease:
        CONTEXT.addTestSeq(TEST_SEQs.dl_unhandledReleaseEvent)
        return requestError("Release event could not be handled for repo '"+repoName+"'!")


    if repoConfig:
        # white/blacklists
        whitelist = repoConfig.get("whitelistedBranches")
        blacklist = repoConfig.get("blacklistedBranches")
        matchWhitelist = list(filter(lambda x: re.compile(x).match(deployInfo.pullBranch), whitelist)) if whitelist else list()
        matchBlacklist = list(filter(lambda x: re.compile(x).match(deployInfo.pullBranch), blacklist)) if blacklist else list()
        if not matchWhitelist and len(matchWhitelist) == 0:
            stop = True
            LOGGER.info("'"+ deployInfo.pullBranch +"' not on whitelist!")
        if len(matchBlacklist) > 0:
            stop = True
            LOGGER.info("'"+ deployInfo.pullBranch +"' is on blacklist!")

        # current Branch is releaseOnly Branch
        if repoConfig.get("releasesOnly") :
            releasesOnlyConfig = repoConfig["releasesOnly"]
            if type(releasesOnlyConfig) == bool and branch == "master":
                releaseOnly = releasesOnlyConfig

            elif type(releasesOnlyConfig) == dict:
                releaseOnly = bool(releasesOnlyConfig.get(branch))
        
        # current Branch is tagsOnly Branch
        if repoConfig.get("tagsOnly") :
            tagsOnlyConfig = repoConfig["tagsOnly"]
            if type(tagsOnlyConfig) == bool and branch == "master":
                tagsOnly = tagsOnlyConfig

            elif type(tagsOnlyConfig) == dict:
                tagsOnly = bool(tagsOnlyConfig.get(branch))


    if releaseOnly:
        LOGGER.info("'"+ deployInfo.branchName + "' is in releaseOnly mode!")
        
        if not release.isSupported:
            CONTEXT.addTestSeq(TEST_SEQs.dl_releaseNotSupported)
            return requestError("Release Only branches are not supported for " + settings.apiName + " API!")
        
    if tagsOnly:
        LOGGER.info("'"+ deployInfo.branchName + "' is in tagsOnly mode!")
    
    # try to get latestReleaseTag
    if ((releaseOnly and not release.latestReleaseTag and not settings.invalidCredentials) or
        (tag == "latestRelease" and not webhook)):
        release.getLatestReleaseTag(repoName)
    
    if tag == "latestRelease" and not webhook:
        releaseOnly = True

    # disabled auto deployment (per file or config)
    if stop or os.path.exists(os.path.join(deployInfo.repoPath, "disabled")) or os.path.exists(os.path.join(deployInfo.repoPath, "disabled-" + deployInfo.branchName)):
        if not force:
            if stop:
                CONTEXT.addTestSeq(TEST_SEQs.dl_autoDeployConfigDisabled)
                return Response("Auto deployment for branch ('"+ deployInfo.branchName +"') in config disabled, add query param 'force=1' to deploy anyway.", content_type=contenttype)
            else:
                CONTEXT.addTestSeq(TEST_SEQs.dl_autoDeployFileDisabled)
                return Response("Auto deployment for branch ('" + deployInfo.branchName + "') per file disabled, add query param 'force=1' to deploy anyway.", content_type=contenttype)
        else:
            if stop:
                CONTEXT.addTestSeq(TEST_SEQs.dl_autoDeployConfigDisabledOW)
                output += "[!] Auto deployment for branch ('"+ deployInfo.branchName +"') in config disabled, ignoring this and deploy anyway...\n\n"
            else:
                CONTEXT.addTestSeq(TEST_SEQs.dl_autoDeployFileDisabledOW)
                output += "[!] Auto deployment for branch ('" + deployInfo.branchName + "') per file disabled, ignoring this and deploy anyway...\n\n"



    if (releaseOnly or tagsOnly) and not tag and not webhook:
        # release or tags only branch, but no tag specified
        error = True
        if releaseOnly and not ignoreRelease:
            CONTEXT.addTestSeq(TEST_SEQs.dl_tagRequiredNoTag)
            return requestError("This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" +
                                "But there is no tag specified in the request. Set tag to... \n"+
                                "... a tag name at your repo to deploy the tag,\n" +
                                "...'latestRelease' to deploy the latest release,\n"+
                                "...'latest' to deploy the latest tag.\n\n" +
                                "You can also add query param 'ignoreRelease=1' to URL to deploy to latest push.")
        elif tagsOnly and not ignoreTag:
            CONTEXT.addTestSeq(TEST_SEQs.dl_tagRequiredNoTag)
            return requestError("This branch '" + deployInfo.branchName + "' has tagsOnly mode enabled.\n" +
                                "But there is no tag specified in the request. Set tag to... \n"+
                                "... a tag name at your repo to deploy the tag,\n" +
                                "...'latestRelease' to deploy the latest release,\n"+
                                "...'latest' to deploy the latest tag.\n\n" +
                                "You can also add query param 'ignoreTag=1' to URL to deploy to latest push.")

        elif releaseOnly and ignoreRelease:
            CONTEXT.addTestSeq(TEST_SEQs.dl_tagRequiredNoTagOW)
            error = False
            output += "[!] Auto deployment for branch ('" + deployInfo.branchName + "') only enabled for releases. Ignoring this and deploy anyway...\n\n"
            
        elif tagsOnly and ignoreTag:
            CONTEXT.addTestSeq(TEST_SEQs.dl_tagRequiredNoTagOW)
            error = False
            output += "[!] Auto deployment for branch ('" + deployInfo.branchName + "') only enabled for tags. Ignoring this and deploy anyway...\n\n"
        
        if error:
            return requestError()
           

    if releaseOnly and not release.latestReleaseTag and tag and not webhook:
        # latest release unknown on releaseOnly branch (manual deploy)
        if not ignoreRelease:
            # abort
            CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyRelUnknown)
            
            if settings.invalidCredentials:
                return requestError("This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" +
                                    "But latest release version is unkown, because of invalid login credentials in config.py!\n" +
                                    "To deploy to tag '"+tag+"', add query parameter 'ignoreRelease=1' to the URL.")
            else:
                return requestError("This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" +
                                    "But there is no published release available yet.\n" +
                                    "To deploy to tag '"+tag+"' anyway, add query parameter 'ignoreRelease=1' to the URL.")
        else:
            CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyRelUnknownOW)
            output += "[!] Auto deployment for branch ('"+ deployInfo.branchName +"') only enabled for releases. Ignoring this and deploy anyway...\n\n"
        
    elif releaseOnly and not release.latestReleaseTag and release.isRelease and webhook:
        # latest release unknown on releaseOnly branch (auto deploy), abort
        code = 500
        
        # is release event
        if settings.invalidCredentials:
            # invalid credentials
            temp = "This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" + \
                   "Latest release version is unkown, because of invalid login credentials in config.py. \n" + \
                   "Stop doing anything. Get the configuration right to allow Deployer to fetch the latest release tag."
        else:
            # valid credentials
            temp = "This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" + \
                   "No (latest) release currently available/published! \n" + \
                   "Stop doing anything."
            code = 400
        
        CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyRelUnknown)
        return requestError(temp, code=code)
    
    elif tagsOnly and not tag and webhook:
        # tagsOnly without tag (auto deploy)
        CONTEXT.addTestSeq(TEST_SEQs.dl_tagRequiredNoTag)
        
        temp = "This branch '" + deployInfo.branchName + "' has tagOnly mode enabled.\n" + \
               "Current event is not a tag create event.\nAborting..."
        return requestError(temp, code=200)
    
    
    elif releaseOnly and not release.isRelease and webhook:
        # other event (e.g. push, ...)
        temp = "This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" + \
                "Current event is not a release event.\nAborting..."
            
        CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyNoRelease)
        return requestError(temp, code=200)
    
    

    firstSetup = False
    # deploy
    if not os.path.exists(deployInfo.repoPath):
        # clone git repo
        try:
            os.makedirs(deployInfo.repoPath, exist_ok=True)
        except:
            pass

        args = ["git", "clone", "-b", deployInfo.pullBranch, deployInfo.gitUrl, "."]
        gitOut, gitError = call(args, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + " ".join(args), gitOut, gitError)
        error |= gitError

        if gitError:
            shutil.rmtree(deployInfo.repoPath, ignore_errors=True)

        firstSetup = True
    else:
        # pull from repo
        cmd = ["git", "clean", "-d", "-f"]
        gitOut, gitError = call(cmd, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "reset", "--hard"]
        gitOut, gitError = call(cmd, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "checkout", deployInfo.pullBranch]
        gitOut, gitError = call(cmd, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "fetch"]
        gitOut, gitError = call(cmd, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError

        cmd = ["git", "reset", "--hard", "origin/" + deployInfo.pullBranch]
        gitOut, gitError = call(cmd, cwd=deployInfo.repoPath)
        output += addOutput("[+] " + ' '.join(cmd), gitOut, gitError)
        error |= gitError



    # check for newest tag
    if tag:
        # get all tags
        gitOut, gitError = call(["git", "tag", "--sort=-committerdate"], cwd=deployInfo.repoPath)

        if gitError:
            output += addOutput("[+] git tag --sort=-committerdate", gitOut, gitError)
            error |= gitError

        gitOut = gitOut.strip()
        gitTags = gitOut.splitlines()
        tagsAnnotated = list(map(lambda x: x.strip(), gitTags[:]))

        if tag == "latest" and not webhook:
            # only manual deploy
            
            if len(gitTags) > 0:
                CONTEXT.addTestSeq(TEST_SEQs.dl_nwhTagLatest)
                tag = gitTags[0]
                output += "[+] Switch to latest tag ('" + tag +"') on ('"+deployInfo.branchName+"')\n\n"
            else:
                CONTEXT.addTestSeq(TEST_SEQs.dl_noTagsAvailable)
                output = "ATTENTION!\nNo tag available, switch to latest push.\n\n\n===========================\n" + output
                output += "[!] Switch to latest push\n\n"
                tag = None

        if tag == "latestRelease" and not webhook:
            
            # only manual deploy
            if len(gitTags) > 0 and release.latestReleaseTag:
                CONTEXT.addTestSeq(TEST_SEQs.dl_nwhTagLatestRelease)
                
                tag = release.latestReleaseTag
                output += "[+] Switch to latest release ('" + tag + "') on ('" + deployInfo.branchName + "')\n\n"
            else:
                output = "ATTENTION!\nNo release available, switch to latest push.\n\n\n===========================\n" + output
                output += "[!] Switch to latest push\n\n"
                tag = None


        # tag exists
        if tag in gitTags:
            tagNumber = gitTags.index(tag)
            releaseTagNumber = -1 if not release.latestReleaseTag else gitTags.index(release.latestReleaseTag)
            
            tagsAnnotated[tagNumber] = "%s <= specified tag" % tagsAnnotated[tagNumber]
            if releaseTagNumber > -1:
                tagsAnnotated[releaseTagNumber] = "%s <= latest published release" % tagsAnnotated[releaseTagNumber]
            
            
            historyOfTags = "History of tags (newest top, oldest bottom):\n" + \
                              "%s" % '\n'.join(map(lambda x: "  %s" % x, tagsAnnotated))
            
            # conutinue condition
            if (releaseOnly and release.isLatestRelease(tag)) or \
               (not releaseOnly and tagNumber == 0):
                # do nothing, just continue without warnings
                pass
            
            # not releaseOnly branch
            elif not releaseOnly and tagNumber > 0 and not webhook:
                # not the newest tag (manual deploy)
                if not ignoreTagDate:
                    CONTEXT.addTestSeq(TEST_SEQs.dl_notNewestTag)
                    temp = "ATTENTION!\n" + \
                           "Specified tag ('%s') is not the newest on this branch. Will set tag to the newest one ('%s').\n" % (tag, gitTags[0]) + \
                           "If you want to checkout your tag anyway, add query param 'ignoreTagDate=1' to URL.\n" + \
                           historyOfTags + "\n\n" + \
                           "If you want to silence this warning, specify the latest tag or set the tag name to 'latest'\n"+\
                           "to always deploy the latest tag.\n\n\n===========================\n"
                    output = temp + output
                    tag = gitTags[0]
                    output += "[!] Set tag to '" + tag + "' (look at the attention section above)\n\n"
                    
                else:
                    CONTEXT.addTestSeq(TEST_SEQs.dl_notNewestTagOW)
                    # not the newest tag, overriding (manual deploy)
                    output += "[!] Specified tag ('%s') is not the newest on this branch.\n" % gitTags[0] + \
                              "    Ignoring this and checking out '%s' anyway...\n\n" % gitTags[0]
                
            elif not releaseOnly and tagNumber > 0 and webhook:
                # not the newest tag (auto deploy)
                CONTEXT.addTestSeq(TEST_SEQs.dl_notNewestTag)
                temp = "ATTENTION!\n" + \
                       "Specified tag ('%s') is not the newest on this branch. Setting tag to the newest one ('%s').\n" % (tag, gitTags[0]) + \
                       historyOfTags + "\n\n" + \
                       "Invocation per webhook only pulls latest tag version.\n\n\n===========================\n"
    
                output = temp + output
                tag = gitTags[0]
                output += "[!] Set tag to '" + tag + "' (look at the attention section above)\n\n"



            # releaseOnly branch, latest release known
            elif releaseOnly and not release.isLatestRelease(tag) and release.latestReleaseTag and not webhook:
                # not latest release (manual deploy)
                if not ignoreRelease:
                    CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnown)
                    temp = "ATTENTION!\nreleaseOnly Mode is enabled for this branch ('" + deployInfo.branchName + "').\n" + \
                           "Specified tag is not the newest release. Setting tag to '"+ release.latestReleaseTag +"'.\n" + \
                           historyOfTags + "\n\n" + \
                           "To deploy the specified tag anyway, add query prameter 'ignoreRelease=1' to URL.\n\n\n===========================\n"
                    output = temp + output
                    tag = release.latestReleaseTag
                    output += "[!] Set tag to '" + tag + "' (look at the attention section above)\n\n"
                else:
                    CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnownOW)
                    # not latest release, overriding
                    temp = "ATTENTION!\nreleaseOnly Mode is enabled for this branch ('" + deployInfo.branchName + "').\n" + \
                           "Specified tag is not the newest release." + \
                           historyOfTags + "\n\n" + \
                           "Ignoring this and checking out this tag ('" + tag + "') anyway...\n\n\n===========================\n"
                    output = temp + output

            elif releaseOnly and not release.isLatestRelease(tag) and release.latestReleaseTag and webhook:
                CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnown)
                # not latest release and releaseOnly branch (auto deploy)
                temp = "ATTENTION!\nreleaseOnly Mode is enabled for this branch ('" + deployInfo.branchName + "').\n" + \
                       "Specified release is not the newest release. Invocation per webhook only pulls latest release.\n" + \
                       historyOfTags + "\n\n" + \
                       "Set deploying version to tag '"+ release.latestReleaseTag +"'\n\n\n===========================\n"
                output = temp + output
                tag = release.latestReleaseTag
                output += "[!] Set tag to '" + tag + "' (look at the attention section above)\n\n"



            # releaseOnly branch, latest release unknown
            elif releaseOnly and not release.latestReleaseTag and ignoreRelease and not webhook:
                CONTEXT.addTestSeq(TEST_SEQs.dl_releaseOnlyRelUnknownOW)
                # latest release unknown, overriding (manual deploy)
                temp = "ATTENTION!\n" + \
                       "This branch '" + deployInfo.branchName + "' has releaseOnly mode enabled.\n" + \
                       historyOfTags + "\n\n" + \
                       "Latest release version is unkown, ignoring this and deploying to tag '"+ tag +"' anyway...\n\n\n===========================\n"
                output = temp + output


    # checkout tag
    if tag and os.path.exists(deployInfo.repoPath):
        verOut, verErr = call("git checkout " + str(tag), cwd=deployInfo.repoPath, shell=True)
        output += addOutput("[+] git checkout " + str(tag), verOut, verErr)
        error |= verErr
        if verErr:
            CONTEXT.addTestSeq(TEST_SEQs.dl_checkoutFailed)
            
    elif not os.path.exists(deployInfo.repoPath) and tag:
        CONTEXT.addTestSeq(TEST_SEQs.dl_checkoutPathNotAvailable)
        output += "[!] skip checkout version, deployment path doesn't exist. Check logs!\n\n"


    # scripts
    if firstSetup and not error:
        # launch setup script
        if os.path.exists(os.path.join(deployInfo.repoPath, "setup")):
            setupOut, setupErr = call([os.path.join(deployInfo.repoPath, "setup"), deployInfo.branchName, request.headers["Host"]], cwd=deployInfo.repoPath)
            output += addOutput("[+] Setup Script", setupOut, setupErr)
            error |= gitError
        else:
            output += "[!] No setup script found\n\n"
    elif not error:
        # launch reload script
        if os.path.exists(os.path.join(deployInfo.repoPath, "reload")):
            relOut, relErr = call([os.path.join(deployInfo.repoPath, "reload"), deployInfo.branchName, request.headers["Host"]], cwd=deployInfo.repoPath)
            output += addOutput("[+] Reload script", relOut, relErr)
            error |= relErr
        else:
            output += "[!] No reload script found\n\n"
    elif error:
        output += "[!] Skip reload or setup script (deploying failed)\n\n"

    output = output.strip()


    # webserver response
    if error:
        output = "Automatic deploy failed!\n========================\n".upper() + output
        return requestError(output, code=500)

    else:
        CONTEXT.addTestSeq(TEST_SEQs.dl_deploySuccess)
        output += "\n\nOverall success!"
        return Response(output, content_type=contenttype)





def createTagEvent(repoName, tag, settings, release):
    repoConfig = CONTEXT.CONFIG.get(repoName)
    if not repoConfig or not repoConfig.get("tagsOnly"):
        return Response("No tag event configured for repo '" + repoName + "'!", content_type=contenttype)
    
    tagsOnlyConfig = repoConfig["tagsOnly"]
    tagsOnlyBranches = []
    
    # get tagsOnly branches
    if type(tagsOnlyConfig) == bool and tagsOnlyConfig:
        tagsOnlyBranches.append("master")
    elif type(tagsOnlyConfig) == dict:
        for k, v in tagsOnlyConfig.items():
            if v:
                tagsOnlyBranches.append(k)
    
    if len(tagsOnlyBranches) == 0:
        return requestError("No branch set to tagsOnly mode. Ignoring this event.", code=500)
    
    output = ''
    error = 200
    for branch in tagsOnlyBranches:
        output += "Start to deploy tag to '" + branch + "'...\n" + \
                  "=============================" + "\n"
        resp = downloadFromGit(repoName, settings, branch=branch, tag=tag, webhook=True, release=release)
        output += resp.get_data(as_text=True) + "\n" + \
                  "Finished with status code: %d\n\n\n" % resp.status_code
        if resp.status_code > error:
            error = resp.status_code
    
    return Response(output, status=error, content_type=contenttype)




def releaseEvent(repoName, tag, settings, release):
    release.isRelease = True
    release.getLatestReleaseTag(repoName)
    
    repoConfig = CONTEXT.CONFIG.get(repoName)
    if not repoConfig or not repoConfig.get("releasesOnly"):
        return Response("No release event configured for repo '" + repoName + "'!", content_type=contenttype)
    
    releasesOnlyConfig = repoConfig["releasesOnly"]
    releasesOnlyBranches = []
    
    # get releaseOnly branches
    if type(releasesOnlyConfig) == bool and releasesOnlyConfig:
        releasesOnlyBranches.append("master")
    elif type(releasesOnlyConfig) == dict:
        for k,v in releasesOnlyConfig.items():
            if v:
                releasesOnlyBranches.append(k)

    if len(releasesOnlyBranches) == 0:
        return requestError("No branch set to releaseOnly mode. Ignoring this event.", code=500)

    
    output = ''
    error = 200
    for branch in releasesOnlyBranches:
        output += "Start to deploy release to '" + branch + "'...\n" + \
                  "=============================" + "\n"
        resp = downloadFromGit(repoName, settings, branch=branch, tag=tag, webhook=True, release=release)
        output += resp.get_data(as_text=True) + "\n" +\
                  "Finished with status code: %d\n\n\n" % resp.status_code
        if resp.status_code > error:
            error = resp.status_code

    return Response(output, status=error, content_type=contenttype)


def reloadConfig(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        CONTEXT.reloadCONFIG()
        return func(*args, **kwargs)
    return wrapper


@app.route('/github', methods=["GET", "POST"])
@reloadConfig
def github():
    settings = APISettings("github")

    headers = request.headers
    jsonData = request.get_json(silent=True)

    if CONTEXT.DEBUG and not CONTEXT.TESTING:
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
        LOGGER.critical("No json data in request! Expected a request with an application/json body.")
        return requestError("No json data in request! Expected a request with an application/json body.")

    if "X-GitHub-Delivery" not in headers or "X-GitHub-Event" not in headers or "GitHub-Hookshot" not in headers["User-Agent"]:
        LOGGER.critical("Unsupported Header combination:\n" + "\n".join(map(lambda x: "    \"%s\": \"%s\"" %(x[0], x[1]), headers.items())))
        return requestError("Invalid Request")


    # calculate HMAC
    if settings.hmacSecret and "X-Hub-Signature" in headers:
        secret = settings.hmacSecret
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
    release = Release(settings)
    event = headers["X-GitHub-Event"]

    if event == "push":
        if "refs/heads" not in jsonData["ref"]:
            LOGGER.debug("No branch push detected, ignore push event.")
            return Response("No branch push detected, ignore push event", content_type=contenttype)

        branch = jsonData["ref"].replace("refs/heads/", "")
        return logErrorRespToLevel(downloadFromGit(repoName, settings, branch=str(branch), release=release, webhook=True), LOGGER.critical)

    elif event == "release":
        tag = jsonData["release"]["tag_name"]
        return logErrorRespToLevel(releaseEvent(repoName, tag, settings, release), LOGGER.critical)

    elif event == "create" and jsonData["ref_type"] == "tag":
        tag = jsonData["ref"]
        return logErrorRespToLevel(createTagEvent(repoName, tag, settings, release), LOGGER.critical)

    elif event == "ping":
        events = jsonData["hook"]["events"]
        supportedEvents = ["push", "release", "create"]
        contentType = jsonData["hook"]["config"]["content_type"]
        
        for a in supportedEvents:
            try:
                events.remove(a)
            except:
                pass
            
        output = ""
        error = False
        if len(events) > 0:
            output += "[-] Unsupported webhook events configured: " + ", ".join(events) + "\n"
            error = True
            
        if contentType != "json":
            output += "[-] Unsupported content type. Expected application/json content type in configuration."
            error = True
            
        if error:
            return requestError(output, code=400)
        else:
            return Response("Everything looks good!", content_type=contenttype)

    else:
        LOGGER.critical("Received an unsupported GitHub Event: "  + headers["X-GitHub-Event"])
        return requestError("Received an unsupported GitHub Event", code=405)
    

@app.route('/gitlab', methods=["GET", "POST"])
@reloadConfig
def gitlab():
    settings = APISettings("gitlab")

    headers = request.headers
    jsonData = request.get_json(silent=True)

    if not jsonData:
        LOGGER.critical("No json data in request! Expected a request with an application/json body.")
        return requestError("No json data in request! Expected a request with an application/json body.")

    if "X-Gitlab-Event" not in headers:
        LOGGER.critical("Unsupported Header combination:\n" + "\n".join(map(lambda x: "    \"%s\": \"%s\"" %(x[0], x[1]), headers.items())))
        return requestError("Invalid Request")

    if settings.secret and "X-Gitlab-Token" in headers:
        if settings.secret != headers["X-Gitlab-Token"]:
            return requestError("Invalid Signature 401", 401)
    
    else:
        LOGGER.warning("Skip signature validation!")


    # setup git operation
    repoName = jsonData["repository"]["name"]
    
    if headers["X-Gitlab-Event"] == "Push Hook":
        if "refs/heads" not in jsonData["ref"]:
            LOGGER.debug("No branch push detected, ignore push event.")
            return Response("No branch push detected, ignore push event", content_type=contenttype)

        branch = jsonData["ref"].replace("refs/heads/", "")
        return logErrorRespToLevel(downloadFromGit(repoName, settings, branch=str(branch), webhook=True), LOGGER.critical)
    
    elif headers["X-Gitlab-Event"] == "Tag Push Hook" and jsonData["object_kind"] == "tag_push":
        if "refs/tags" not in jsonData["ref"]:
            LOGGER.debug("No tag push detected, ignore push event.")
            return Response("No tag push detected, ignore push event", content_type=contenttype)
        
        tag = jsonData["ref"].replace("refs/tags/", "")
        return logErrorRespToLevel(createTagEvent(repoName, tag, settings, Release(settings)), LOGGER.critical)
    
    else:
        LOGGER.critical("Received an unsupported Gitlab Event: "  + headers["X-Gitlab-Event"])
        return requestError("Received an unsupported Gitlab Event", code=405)


@app.route('/bitbucket', methods=["GET", "POST"])
@reloadConfig
def bitbucket():
    settings = APISettings("bitbucket")
    
    headers = request.headers
    jsonData = request.get_json(silent=True)
    
    if not jsonData:
        LOGGER.critical("No json data in request! Expected a request with an application/json body.")
        return requestError("No json data in request! Expected a request with an application/json body.")
    
    if "X-Event-Key" not in headers or "X-Request-UUID" not in headers or "X-Hook-UUID" not in headers:
        LOGGER.critical("Unsupported Header combination:\n" + "\n".join(map(lambda x: "    \"%s\": \"%s\"" % (x[0], x[1]), headers.items())))
        return requestError("Invalid Request")
    
    
    
    # setup git operation
    if headers["X-Event-Key"] == "repo:push":
        repoName = jsonData["repository"]["name"]
        
        typ = jsonData["new"]["type"]
        
        if typ == "branch":
            branch = jsonData["new"]["name"]
            return logErrorRespToLevel(downloadFromGit(repoName, settings, branch=str(branch), webhook=True), LOGGER.critical)
            
        elif typ == "tag":
            tag = jsonData["new"]["name"]
            return logErrorRespToLevel(createTagEvent(repoName, tag, settings, Release(settings)), LOGGER.critical)
        
        else:
            LOGGER.critical("Received unknown bitbucket push typ: " + typ)
            return requestError("Received an unsupported bibucket push typ: " + typ, code=405)
        
    else:
        LOGGER.critical("Received an unsupported Gitlab Event: " + headers["X-Gitlab-Event"])
        return requestError("Received an unsupported Gitlab Event", code=405)
    
        

def requiresAuth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CONTEXT.PROTECTION_COOKIE and not CONTEXT.PROTECTION:
            # no protection configured
            return func(*args, **kwargs)
        
        auth = request.authorization
        cookie = None
        respStr = "Authentication"
        
        # store result of func temporarily
        resp = None
        
        # read the cookie from request, if a cookie is set in configuration
        if CONTEXT.PROTECTION_COOKIE:
            cookie = request.cookies.get(CONTEXT.PROTECTION_COOKIE["name"])
        
        if auth and CONTEXT.PROTECTION:
            # Authorization
            if auth.username == CONTEXT.PROTECTION["username"] and auth.password == CONTEXT.PROTECTION["password"]:
                resp = func(*args, **kwargs)
            else:
                respStr = "Invalid credentials"

        # check for valid cookie
        if cookie and cookie == CONTEXT.PROTECTION_COOKIE["value"]:
            resp = func(*args, **kwargs)
        
        if resp:
            # set cookie to resp
            if CONTEXT.PROTECTION_COOKIE:
                if not isinstance(resp, Response):
                    resp = Response(resp)
                
                max_age = 31536000 if not CONTEXT.PROTECTION_COOKIE["maxAge"] else CONTEXT.PROTECTION_COOKIE["maxAge"]
                httponly = True
                path = "/" if not CONTEXT.PROTECTION_COOKIE["path"] else CONTEXT.PROTECTION_COOKIE["path"]
                secure = False if not CONTEXT.PROTECTION_COOKIE["secureFlag"] else CONTEXT.PROTECTION_COOKIE["secureFlag"]

                resp.set_cookie(CONTEXT.PROTECTION_COOKIE["name"], CONTEXT.PROTECTION_COOKIE["value"], max_age=max_age, httponly=httponly, secure=secure, path=path)
                
            return resp
        
        # send WWW-Authenticate Header
        return Response(respStr, status=401, headers={"WWW-Authenticate": "Basic realm=\"Deployer\""})
        
    return wrapper



@app.route('/deploy/<repoName>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>', methods=["GET", "POST"])
@app.route('/deploy/<repoName>/<branch>/<tag>', methods=["GET", "POST"])
@reloadConfig
@requiresAuth
def deploy(repoName, branch="master", tag=None):
    
    if request.method == "GET":
        return Response('<form method="POST"><input id="button" type="submit" value="Start"></form><script>document.getElementById("button").focus();</script>')

    # get API for repoName
    repoSettings = CONTEXT.CONFIG.get(repoName)
    api = None
    
    if repoSettings:
        api = repoSettings.get("api")

    if not api:
        api = CONTEXT.CONFIG.get("defaultApi")

    if not api:
        CONTEXT.addTestSeq(TEST_SEQs.deploy_repoConfigNoApi)
        return requestError("No API specified, can't continue")

    # build APISettings object
    settings = APISettings(api)

    return logErrorRespToLevel(downloadFromGit(repoName, settings, branch=branch, tag=tag, webhook=False), LOGGER.warning)



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
    app.run(debug=CONTEXT.DEBUG)

