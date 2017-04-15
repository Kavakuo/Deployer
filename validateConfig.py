#!/usr/bin/env python3

# coding=utf-8
import config
import logging.handlers
import logging, sys
import src.utils.logger as logger


LOGGER = logger.loggerWithName("Deployment")

STREAM_HANDLER = logger.StreamHandler(sys.stdout)
LOGGER.addHandler(logger.configureHandler(STREAM_HANDLER, logger.logging.Formatter()))
LOGGER.setLevel(logger.logging.DEBUG)

def validateGeneralApiConfig(c, apiName):
    deployPath = c.pop("deployPath", None)
    baseUrl = c.pop("baseUrl", None)
    
    assert deployPath, "'deployPath' key missing in '" + apiName + "' configuration"
    assert baseUrl, "'baseUrl' key missing in '" + apiName + "' configuration"
    
    assert isinstance(deployPath, str), "'deployPath' must be a String"
    assert isinstance(baseUrl, str), "'baseUrl' must be a String"


def validateGithub(a):
    validateGeneralApiConfig(a, "github")
    
    accessToken = a.pop("accessToken", None)
    username = a.pop("username", None)
    hmacSecret = a.pop("hmacSecret", None)
    
    if not accessToken:
        LOGGER.info("ReleaseOnly mode not supported for private repositories, github 'accessToken' is missing.")
    else:
        assert isinstance(accessToken, str), "'accessToken' must be a String"
        
    if not username:
        LOGGER.info("ReleaseOnly mode not supported for private repositories, github username is missing.")
    else:
        assert isinstance(username, str), "'username' must be a String"
        
    if not hmacSecret:
        LOGGER.info("Signature of github webhook post requests can't be validated. 'hmacSecret' key is missing in configuration.")
    else:
        assert isinstance(hmacSecret, bytes), "'hmacScret' must be bytes"
        
    assert len(a.keys()) == 0, "Unknown keys in github dictionary found: " + ", ".join(a.keys())
    

def validateGitlab(a):
    validateGeneralApiConfig(a, "gitlab")
    
    secret = a.pop("secret", None)
    if not secret:
        LOGGER.info("Gitlab webhook post requests can't be validated. 'secret' key is missing in dictionaroy.")
    else:
        assert isinstance(secret, str), "'secret' must be a String"

    assert len(a.keys()) == 0, "Unknown keys in gitlab dictionary found: " + ", ".join(a.keys())


def validateProtection(p):
    username = p.pop("username", None)
    password = p.pop("password", None)
    
    cookie = p.pop("cookie", None)
    
    if username:
        assert isinstance(username, str), "'username' must be a String"
    if password:
        assert isinstance(password, str), "'password' must be a String"
        
    if cookie:
        name = cookie.pop("name", None)
        val  = cookie.pop("value", None)
        secureFlag = cookie.pop("secureFlag", None)
        path = cookie.pop("path", None)
        maxAge = cookie.pop("maxAge", None)
        
        if name:
            assert isinstance(name, str), "'name' must be a String"
            
        if val:
            assert isinstance(val, str), "'value' must be a String"
            
        if secureFlag:
            assert isinstance(secureFlag, bool), "'secureFlag' must be a Bool"
            
        if path:
            assert isinstance(path, str), "'path' must be a String"
            
        if maxAge:
            assert isinstance(maxAge, int), "'maxAge' must be an Int"

        assert len(cookie.keys()) == 0, "Unknown keys in protection cookie dictionary found: " + ", ".join(cookie.keys())
    
    assert len(p.keys()) == 0, "Unknown keys in 'protection' dictionary found: " + ", ".join(p.keys())
    
    
def validateRepo(repoName, dic):
    assert isinstance(dic, dict), "'"+ repoName + "' configuration must be a dictionary"
    
    whitelist = dic.pop("whitelistedBranches", None)
    blacklist = dic.pop("blacklistedBranches", None)
    
    releaseOnly = dic.pop("releasesOnly", None)
    tagsOnly = dic.pop("tagsOnly", None)
    
    api = dic.pop("api", None)
    
    if whitelist:
        assert isinstance(whitelist, list), "'whitelistedBranches' in '" + repoName + "' configuration must be a list"
        for a in whitelist:
            assert isinstance(a, str), "all entries in 'whitelistedBranches' in '" + repoName + "' configuration must be a String"
    
    if blacklist:
        assert isinstance(blacklist, list), "'whitelistedBranches' in '" + repoName + "' configuration must be a list"
        for a in blacklist:
            assert isinstance(a, str), "all entries in 'whitelistedBranches' in '" + repoName + "' configuration must be a String"
    
    if releaseOnly:
        assert isinstance(releaseOnly, dict) or isinstance(releaseOnly, bool), "'releasesOnly' in '" + repoName + "' configuration must be a dictionary or bool"
        if isinstance(releaseOnly, dict):
            for k, v in releaseOnly.items():
                assert isinstance(k, str), "keys in 'releaseOnly' dictionary in '" + repoName + "' configuration must be a String"
                assert isinstance(v, bool), "values in 'releaseOnly' dictionary in '" + repoName + "' configuration must be a Bool"
            
    if tagsOnly:
        assert isinstance(tagsOnly, dict) or isinstance(tagsOnly, bool), "'tagsOnly' in '" + repoName + "' configuration must be a dictionary or bool"
        if isinstance(tagsOnly, dict):
            for k, v in tagsOnly.items():
                assert isinstance(k, str), "keys in 'tagsOnly' dictionary in '" + repoName + "' configuration must be a String"
                assert isinstance(v, bool), "values in 'tagsOnly' dictionary in '" + repoName + "' configuration must be a Bool"
    
    if api:
        assert isinstance(api, str), "'api' in '" + repoName + "' configuration must be a String"
        assert api == "github" or api == "bitbucket" or api == "gitlab", "unsupported value for 'api' in '" + repoName + "' configuration. Supported values are: github, gitlab, bitbucket"
    
    assert len(dic.keys()) == 0, "Unsupported keys in '" + repoName + "' configuration found: " + ", ".join(dic)
    

def main():
    CONFIG = config.CONFIG
    
    LOGGER.info("[!] If this script fails, your configuration file is corrupted. Run this again to validate the configuration again until it finishes.")

    defaultApi = CONFIG.pop("defaultApi", None)
    logger = CONFIG.pop("mailLogger", None)
    
    if defaultApi:
        assert isinstance(defaultApi, str), "'defaultApi' must be a string"
        assert defaultApi == "github" or defaultApi == "gitlab" or defaultApi == "bitbucket", "Invalid defaultApi! Supported values are: github, gitlab, bitbucket"
    
    if logger:
        assert isinstance(logger, logging.handlers.SMTPHandler), "'mailLogger' needs to be an instance of logging.handlers.SMTPHandler"
        
    
    # validate protection configuration
    protection = CONFIG.pop("protection", None)
    validateProtection(protection)


    # validate API Configurations
    github = CONFIG.pop("github", None)
    gitlab = CONFIG.pop("gitlab", None)
    bitbucket = CONFIG.pop("bitbucket", None)

    assert github or gitlab or bitbucket, "You need at least one API configuration to use Deployer!"
    
    if github:
        validateGithub(github)
    
    if gitlab:
        validateGitlab(gitlab)
        
    if bitbucket:
        validateGeneralApiConfig(bitbucket, "bitbucket")
        assert len(bitbucket.keys()) == 0, "Unknown keys in 'bitbucket' dictionary found: " + ", ".join(bitbucket.keys())
    
    
    # validate repo configurations
    repos = []
    for repo in CONFIG.keys():
        repos.append(repo)
        
    LOGGER.info("[+] Detected repository configurations: " + ", ".join(repos))
    
    for a in repos:
        validateRepo(a, CONFIG[a])

    LOGGER.info("[+] config file looks good. Go ahead!")




if __name__ == '__main__':
    main()