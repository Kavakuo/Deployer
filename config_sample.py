# coding=utf-8

import logging.handlers

CONFIG = {
    "mailLogger": logging.handlers.SMTPHandler(),
    "defaultApi": "API_NAME", # optional
    
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