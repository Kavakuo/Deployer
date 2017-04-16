# coding=utf-8

from utils import logger
import requests, os
import requests.auth
from context import CONTEXT

LOGGER = logger.logging.Logger("logger")




class APISettings(object):
    def __init__(self, apiName):
        self.apiName = apiName
        self.rawApiSettings = CONTEXT.CONFIG.get(self.apiName) if CONTEXT.CONFIG.get(self.apiName) else dict()
        self.baseUrl = self.rawApiSettings.get("baseUrl")
        self.deployPath = self.rawApiSettings.get("deployPath")
        if self.deployPath[-1] != "/":
            self.deployPath += "/"
        
        # GitHub, repo API access (to get the latest release)
        self.accessToken = self.rawApiSettings.get("accessToken")
        self.username = self.rawApiSettings.get("username")
        self.hmacSecret = self.rawApiSettings.get("hmacSecret")
        self.invalidCredentials = False
        
        # Gitlab special
        self.secret = self.rawApiSettings.get("secret")
    
    def deployPossible(self):
        if not self.baseUrl or not self.deployPath:
            return False
        return True


class Release(object):
    def __init__(self, settings, isRelease=False):
        self.latestReleaseTag = None
        self.isRelease = isRelease
        self._tried = False
        self.settings = settings
        
        if self.settings.apiName == "github":
            self.isSupported = True
        else:
            self.isSupported = False
    
    def getLatestReleaseTag(self, repoName):
        """
        This method should deliver the tagname of the latest published release.

        :param repoName: get the latestRelease from repoName
        :type repoName: str

        """
        
        if self._tried or not self.isSupported:
            return
        
        if self.settings.apiName == "github":
            # get latest release from github
            if not self.settings.accessToken:
                LOGGER.warning("Missing Access Token! Take a look at config.py.")
            
            if not self.settings.username:
                LOGGER.warning("Username unknown! Take a look at config.py.")
            
            baseUrl = "https://api.github.com/repos/" + self.settings.username + "/" + repoName
            url = baseUrl + "/releases/latest"
            auth = None
            if self.settings.username and self.settings.accessToken:
                auth = requests.auth.HTTPBasicAuth(self.settings.username, self.settings.accessToken)
            
            resp = requests.get(url, auth=auth).json()
            self.latestReleaseTag = resp.get("tag_name")
            
            if CONTEXT.TESTING:
                # manual overriding for tests because requests can fail (GitHub API Limit)
                self.latestReleaseTag = "dev22"
                
                if CONTEXT.CONFIG["github"]["username"] != "Kavakuo":
                    self.latestReleaseTag = None
                    self.settings.invalidCredentials = True
            
            elif not self.latestReleaseTag:
                # testing credentials
                resp = requests.get(baseUrl, auth=auth).json()
                
                if not resp.get("name"):
                    # invalid accessToken
                    self.settings.invalidCredentials = True
                else:
                    # no releases
                    pass
        
        self._tried = True
        if not self.latestReleaseTag and not self.settings.invalidCredentials:
            msg = "No Release found!"
            LOGGER.warning(msg)
            CONTEXT.addTestSeq(TEST_SEQs.release_noReleaseAvailable)
        elif not self.latestReleaseTag and self.settings.invalidCredentials:
            CONTEXT.addTestSeq(TEST_SEQs.release_invalidCredentials)
            LOGGER.critical("Can't get latest release. Invalid login credentials in config.py found!")
        else:
            LOGGER.debug("Latest release tag is '" + self.latestReleaseTag + "'")
    
    def isLatestRelease(self, tag):
        return tag == self.latestReleaseTag


class DeployInfo(object):
    def __init__(self, settings, repoName, branchName):
        if branchName == "master":
            self.repoPath = settings.deployPath + repoName + "/"
        else:
            self.repoPath = settings.deployPath + repoName + "-" + branchName + "/"
        
        self.gitUrl = settings.baseUrl + repoName + ".git"
        self.branchName = branchName
        self.pullBranch = self.branchName
        self.repoName = repoName
        self.settings = settings
        
        if branchName[0] == ".":
            self.pullBranch = "master"
            self.repoPath = settings.deployPath + repoName + "-" + branchName[1:] + "/"
        
        self.repoPath = os.path.realpath(self.repoPath)
        if self.repoPath[-1] != "/":
            self.repoPath += "/"


class TEST_SEQs(object):
    # Release class
    release_noReleaseAvailable = release_invalidCredentials = 1
    
    # deploy method
    deploy_repoConfigNoApi = 1
    
    # before pulling
    dl_whQueryNotAllowed = dl_unhandledReleaseEvent = dl_autoDeployConfigDisabled = dl_autoDeployFileDisabled = dl_autoDeployConfigDisabledOW = dl_autoDeployFileDisabledOW = 1
    dl_releaseOnlyRelUnknown = dl_releaseOnlyRelUnknownOW = dl_releaseOnlyNoRelease = 1
    dl_tagRequiredNoTag = dl_tagRequiredNoTagOW = 1
    dl_releaseNotSupported = 1
    
    # after pulling, tags
    dl_nwhTagLatest = dl_nwhTagLatestRelease = dl_noTagsAvailable = 1
    dl_notNewestTag = dl_notNewestTagOW = dl_releaseOnlyNotLatestRelRelKnown = dl_releaseOnlyNotLatestRelRelKnownOW = 1
    
    # after pullung, tags
    dl_checkoutFailed = dl_checkoutPathNotAvailable = 1
    
    # overall
    dl_deploySuccess = 1
    
    
# every class attribute is set to its name
attributes = list(filter(lambda x: x[0] != "_", TEST_SEQs.__dict__))
for key in attributes:
    setattr(TEST_SEQs, key, key)