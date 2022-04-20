<a name="top"></a>
<a name="overview"></a>

# Overview

This module was inspired by the [SFTP for Sublime Text](https://codexns.io/products/sftp_for_sublime) plugin.

As such, it facilitates interacting with remote hosts via ssh,<br />
with the added bonus of providing a means to mirror your local<br />
working directory to the specified path on the remote host in order<br />
to facilitate local-edit/remote-build.

With this module you can:

- Edit and manipulate your scripts locally and execute them remotely, <br />
  with file synchronization capabilities
- Map a local folder to a remote folder

# Prerequisites:

- Python 3.7+
- paramiko
- If working with git repos, the module requires that git be installed locally and remotely

# Installation

* From pypi: `pip3 install bertdotssh`
* From this git repo: `pip3 install git+https://github.com/berttejeda/bert.sshutil.git`<br />
  Note: To install a specific version of the library from this git repo, <br />
  suffix the git URL in the above command with @{ tag name }, e.g.: <br />
  git+https://github.com/berttejeda/bert.sshutil.git@1.0.0

# Usage Examples

## Get process status for a remote host via ssh

```python

from bertdotssh.provider import RemoteCLIProvider

settings = {
  'host': 'myhost.example.local', 
  'remote_path': '/home/myusername',
  'port': 22, 
  'ssh_key_file': '~/.ssh/id_rsa', 
  'user': 'myusername'
}

remote = RemoteCLIProvider(settings)

remote.run('ps')
```

## Syncronize local files to remote and run a local script against the same host

Given:
- Local working directory: /home/myusername/some/path
- Local script: myscript.sh

```python

from bertdotssh.provider import RemoteCLIProvider

settings = {
  'host': 'myhost.example.local', 
  'remote_path': '/home/myusername',
  'port': 22, 
  'ssh_key_file': '~/.ssh/id_rsa', 
  'user': 'myusername',
  'sync_no_clobber': True,
  'sync_on': True  
}

remote = RemoteCLIProvider(settings)

remote.run('myscript.sh')
```

## Syncronize local git repo to remote and run a local script against the same host

Given:
- Local working directory (a git repo) at: /home/myusername/some/git/myrepo
- Local script at: /home/myusername/some/git/myrepo/myscript.sh
- Git repo on remote host at: /home/myusername/some/other/path/git/myrepo

```python

from bertdotssh.provider import RemoteCLIProvider

settings = {
  'host': 'myhost.example.local', 
  'remote_path': '/home/myusername/some/other/path/git/myrepo',
  'port': 22, 
  'ssh_key_file': '~/.ssh/id_rsa', 
  'user': 'myusername',
  'sync_no_clobber': True,
  'sync_on': True  
}

remote = RemoteCLIProvider(settings)

remote.run('myscript.sh',
  git_username='my_git_username', 
  git_password='my_git_password')
```

# File syncrhonization behavior

The above example scenarios exhibit the following programmatic behavior upon sync:

1. Determine if local working directory is a git repo
  - If True
      - Determine the URL for the git remote via command `git config --get remote.origin.url`
      - Determine the paths for any locally changed files via command `git diff-index HEAD --name-status`
      - Determine the paths for any untracked files via command `git ls-files --others --exclude-standard`
      - Produce a list of files to sync by combining the output of the above two commands
  - If False
      - Produce a list of files to sync that have changed within the last 5 minutes
2. Determine if remote path exists
  - If False
      - If local is a git repo
        - Perform a git clone of the git repo against the remote path
        - Else, create the remote directory and synchronize the file list across the remote
  - If True, determines if remote path is a git repo
      - Determine set of files that have changed in the remote path
      - If True & sync_no_clobber == True, synchronize locally changed <br />
        files to remote path, skipping any files that have also changed on the remote
      - If True & sync_no_clobber == False, synchronize locally changed <br />
        files to remote path, overwriting any files that have also changed on the remote