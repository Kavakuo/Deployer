# Readme

Cloning is done with:  
`git clone -b [branch] git@github.com:Kavakuo/[repoName].git .`

Pulling is done with:
```bash
git clean -d -f     # cleans all files and directories except paths in ignore file
git reset --hard
git checkout BRANCH
git fetch
git reset --hard origin/BRANCH

git checkout TAG    # optional
```

## Features
* Support for `reload` and `setup` script
    * Put the executable scripts into your root repo folder
    * `setup` is launched after cloning (only on first deployment)
    * `reload` is launched after pulling (for any other deployment)
    * Both scripts take two arguments the branch name and the host field from the HTTP request header
* Cloned repositories are stored at `[deployPath]/[REPO_NAME]-[BRANCH]`
* Option to auto deploy only new releases (github only) or new tags to certain branches/folders.
* Select which branches should auto deploy.
    * Take a look at [config.py](#configpy) file or
    * Put a `disabled[-branchName]` file into your repo or working copy to disable auto deploy.
* Support for GitHub `push`, `release` and `create` (tags only) webhooks
    * `/github` API Endpoint
* Support for Gitlab `Push Events` and `Tag Push Events` webhooks
    * `/gitlab` API Endpoint
* Support for Bitbucket repository `Push` webhooks (branches and tags)
    * `/bitbucket` API Endpoint
* API to deploy manually
    * `/deploy/repoName[/branch[/tag]]`
    * `tag` could be `latest` to deploy the latest tag or `latestRelease` to deploy the latest published release (github only).


## config.py
Rename `config_sample.py` to `config.py` after cloning!

```python
{
    "mailLogger": logging.handlers.SMTPHandler(),
    "defaultApi": "API_NAME", # optional

    "protection": { # optional
        "username":"d",
        "password":"h",
        
        # cookie for manual deployment to avoid a new login on every session
        "cookie": {
            "name": "saveLogin",
            "value": "abc",
            "secureFlag": False,
            "path": "/",
            "maxAge": 31536000
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
        "tagsOnly": {
            "develop":True
        },

        # only required, if defaultAPI is not set
        "api":"API_NAME",
    },
}
```

For a more advanced config file take a look at the `config_test.py` file in the `src/test_data/` folder. This is used for the unittests. To validate the configuration file, launch the included `validateConfig.py` script.


* `mailLogger: logging.handlers.SMTPHandler()`  
[SMTPHandler()](https://docs.python.org/3.6/library/logging.handlers.html#logging.handlers.SMTPHandler) logging handler, to send you mails on certain events (`logging.CRITICAL`).

* `defaultApi: String`  
Every listed or unlisted REPO_NAME without `api`-Key is assumed to be available with `defaultApi`. The value of this key could be `github`, `gitlab` or `bitbucket`. This is only required if you want to use the manual deployment feature.

* `protection: Dictionary`  
Optional dictionary which configures the authentication for the manual deployment feature at the `/deploy` API endpoint.

    * `username: String`  
    The username for the Basic Authentication.

    * `password: String`  
    The password for the Basic Authentication.

    * `cookie: Dictionary`  
    Optional cookie dictionary to support authentication with a cookie to only need login once.

        * `name: String`  
        Name of the login cookie

        * `value: String`  
        Value of the login cookie

        * `secureFlag: Bool` (optional)  
        **Default:** False, if true the cookie is only sent over https.

        * `path: String` (optional)  
        **Default:** "/", path for the cookie.

        * `maxAge: Int` (optional)
        **Default:** 31536000 (1 year), how long the cookie is valid.

* `API_NAME: Dictionary`  
`API_NAME` is a placeholder and could be `github`, `gitlab` or `bitbucket`. Multiple `API_NAME` dictionaries are possible to support multiple services.

    * `gitBaseUrl: String`  
    The repository should be available at `[baseUrl] + [REPO_NAME]`. You can use `ssh` or `https` links.

    * `deployPath: String`  
    Use this to specifiy the parent folder for the deployment. Repos are located at `[deployPath]/[REPO_NAME]-[BRANCH]`.

    * `accessToken: String` 
    API Access Token. Is required for `release` webhooks for GitHub (look at `REPO_NAME[releasesOnly]`). Is used to patch the `gitBaseUrl` for authentication, if http protocol is used for `gitBaseUrl`.

    * `username: String` (GitHub only)  
    GitHub Username. Is required for `release` webhooks (look at `REPO_NAME[releasesOnly]`).    

    * `hmacSecret: bytes` (GitHub only)  
    The secret key to verify the integrity and authentication of the GitHub Messages.

    * `secret: String` (Gitlab only)  
    The secret key to verify the authentication of Gitlab Messages.
    

* `REPO_NAME: Dictionary`  
`REPO_NAME` is a placeholder and should be replaced with the repository name of the repository which you want to use with Deployer. If you don't list the repo in the config file, every branch will be cloned and releaseOnly or tagOnly mode is disabled.

    * `whitelistedBranches: list[String]`  
    Only auto deploy on new pushs/releases on branches in this list.<a href="#regex"><sup>1</sup></a>

    * `blacklistedBranches: list[String]`  
    Do not auto deploy on new pushs/releases on branches in this list.<a href="#regex"><sup>1</sup></a>

    * `releasesOnly: Bool or Dictionary` (GitHub only)  
    Enable the **releaseOnly** mode. Auto deploy only new published releases to specific branches. If you use a bool, new published releases are cloned into the master branch directory. If you use a dictionary, you can enable the releaseOnly mode per branch. When the release event is triggered the release is deployed into all listed branch directories. Every branch name in the dictionary with a leading `.` is based on the master branch but deployed into the folder `[deployPath]/[REPO_NAME]-[BRANCH_NAME (without the leading ".")]`. Only the latest release (by time) is auto deployed. To get the latest release on private repos, a `GitHub Access Token` and the `Username` is needed in the `github` dictionary.

    * `tagsOnly: Bool or Dictionary`  
    Enable the **tagOnly** mode. Auto deploy only new created tags (`create` webhook) to all listed branches. Look above at `releasesOnly` how the Bool or Dictionary is handled. Only the latest tag (sorted by commit date) is auto deployed.

    * `api: String`  
    This is only required if `defaultApi` is not specified and if you want to use the manual deploy feature. It is not needed for auto deployment.


<a name="regex"><sup>1</sup></a> Every entry in this list is handled as regex. It is matched with `re.compile(entry).match(branch)`. [\[Documentation\]](https://docs.python.org/3.6/library/re.html#re.match)

