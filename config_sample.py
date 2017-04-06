import logging.handlers

CONFIG = {
    "REPO_NAME": {
        "whitelistedBranches":["master", "develop"],
        "blacklistedBranches":["feature"]
    },
    "mailLogger": logging.handlers.SMTPHandler(),
    "deployPath": "/home/kavakuo/GitProjects/",
    "gitBaseUrl": "git@github.com:Kavakuo/"
}