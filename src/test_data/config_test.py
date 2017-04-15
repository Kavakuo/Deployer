# coding=utf-8


CONFIG = {
    "defaultApi": "github",
    
    "github": {
        "username": "Kavakuo",
        "baseUrl": "git@github.com:Kavakuo/",
        "hmacSecret": b"topSecret",
        "deployPath": "../TestRepos/"
    },
    
    "gitlab": {
        "deployPath": "../TestRepos/",
        "baseUrl": "https://Kavakuo@gitlab.com/Kavakuo/",
    },
    
    "bitbucket": {
        "deployPath": "../TestRepos/",
        "baseUrl": "https://Kavakuo@bitbucket.org/Kavakuo/"
    },
    
    "TestRepo": {
        "whitelistedBranches": ["master", "develop"],
        "releasesOnly": {
            ".Releases": True
        },
        "tagsOnly": {
            ".Tags": True
        }
        # implied "api":"github" because of the 'defaultApi' key
    },
    
    "TestRepo-Gitlab": {
        "whitelistedBranches": ["master", "develop"],
        "releasesOnly": {
            ".Releases": True
        },
        "tagsOnly": {
            ".Tags": True
        },
        "api":"gitlab"
    },
    
    "TestRepo-Bitbucket": {
        "whitelistedBranches": ["master", "develop"],
        "releasesOnly": {
            ".Releases": True
        },
        "tagsOnly": {
            ".Tags": True
        }
        # api key missing for testing reasons
        # "api": "bitbucket"
    }
}