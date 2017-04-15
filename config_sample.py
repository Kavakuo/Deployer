# coding=utf-8

import logging.handlers

CONFIG = {
    "mailLogger": logging.handlers.SMTPHandler(),
    "defaultApi": "API_NAME", # optional
    
    "protection": {
        # basic authentication for manual deployment
        "username":"d",
        "password":"h",
        
        # cookie for manual deployment to avoid a new login on every session
        "cookie": {
            "name": "saveLogin",
            "value": "abc",
            "secureFlag": False, # optional (default: False)
            "path": "/",         # optional (default: /)
            "maxAge": 31536000   # optional (default: 1 Year)
        }
    },
    
    "API_NAME": {
        "accessToken":"TOKEN",
        "username":"USERNAME",
        "baseUrl": "git@github.com:Kavakuo/",
        "hmacSecret": b"secret",
        "deployPath": "/home/kavakuo/GitProjects/"
    },


    "REPO_NAME": {
        "whitelistedBranches":["master", "develop"],
        "blacklistedBranches":["feature"],
        "releasesOnly": {
            "master":True,
            ".Releases":True
        },

        # only required, if defaultAPI is not set
        "api":"API_NAME",
    },
}