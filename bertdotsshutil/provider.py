# Imports
import logging
from first import first
import os
from os import fdopen, remove
import re
import uuid
import sys
import time
from tempfile import mkstemp
import yaml
# Import third-party and custom modules
from bertdotsshutil.logger import Logger
from bertdotsshutil.dictutils import Struct
from bertdotsshutil.invocation import RemoteCliInvocation
from bertdotsshutil import client

# Setup Logging
logger = Logger().init_logger(__name__)
# Get This Package's name
package_name = __package__.split('.')[0]

if getattr(sys, 'frozen', False):
    # frozen
    self_file_name = os.path.basename(sys.executable)
else:
    self_file_name = os.path.basename(__file__)     

class RemoteCLIProvider:
    
  def __init__(self, settings):

    self.settings = settings
    self.settings_obj = Struct(settings)
    self.remote_dir = self.settings_obj.remote_path
    ssh_client = client.SSHUtilClient(self.settings_obj)
    self.remote_sub_process = RemoteCliInvocation(self.settings, ssh_client)
    self.sftp_sync = ssh_client.sync()
    self.git_repo_http_pattern = re.compile('(htt[\\w]+[\\W]+)(.*)')

  def run(self, remote_command, **kwargs):
    """Execute the underlying subprocess via a remote host"""
    remote_host = self.settings_obj.host
    git_username = first([
      os.environ.get('git_username'),
      kwargs.get('git_username'),
      self.settings.get('git_username')])    
    git_password = first([
      os.environ.get('git_password'),
      kwargs.get('git_password'),
      self.settings.get('git_password')])    
    # Import third-party and custom modules
    local_dir = os.getcwd().replace('\\', '/')
    local_dir_name = os.path.basename(os.getcwd().replace('\\', '/'))
    logger.info('Checking remote path %s' % self.remote_dir)
    sync_on = self.settings_obj.sync_on
    if sync_on:
      self.sync(git_username=git_username, git_password=git_password)
    remote_command_result = self.remote_sub_process.call(self.remote_dir, remote_command, stdout_listen=True)
    if remote_command_result.returncode > 0:
        logger.error('Remote command failed with:')
        if not remote_command_result.stdout:
          print('\n'.join(remote_command_result.stderr))
        else:
          print('\n'.join(remote_command_result.stdout))
        sys.exit(remote_command_result.returncode)
    else:
        print('\n'.join(remote_command_result.stdout))
  
  def mk_remote_dir(self, remote_dir):

    cmd = 'mkdir -p %s' % remote_dir
    mkdir_result = self.remote_sub_process.call('/', cmd)
    if mkdir_result:
        logger.info("Successfully created %s" % remote_dir)
        return True
    else:
        logger.error('Unable to create remote path!')
        return False

  def test_remote_dir(self, remote_dir):

    # Check whether the remote path exists and is a git repo
    cmd = 'echo $(test -d {0} && echo 1 || echo 0),$(cd {0} 2>/dev/null && git status 1> /dev/null 2> /dev/null && echo 1 || echo 0)'.format(remote_dir)
    rmc = self.remote_sub_process.call(self.remote_dir, cmd) or ['0']
    rms = sum([int(n) for n in ''.join(rmc).split(',')])
    rem_is_git = True if rms == 2 else False
    rem_exists = True if rms > 0 else False
    return [rem_exists, rem_is_git]

  def sync(self, **kwargs):

    git_username = kwargs.get('git_username')
    git_password = kwargs.get('git_password')
    loc_is_git = True if os.path.exists('.git') else False
    rem_exists, rem_is_git = self.test_remote_dir(self.remote_dir)
    if rem_is_git:
        logger.info('OK, remote path exists and is a git repo - %s' % self.remote_dir)
    elif rem_exists:
        logger.info('OK, remote path exists - %s' % self.remote_dir)
    else:
      if loc_is_git:
        from pathlib import Path
        remote_dir_path = Path(self.remote_dir).parent
        remote_dir_parent = str(remote_dir_path).replace('\\', '/')
        rem_parent_exists, _ = self.test_remote_dir(remote_dir_parent)
        if not rem_parent_exists:
          self.mk_remote_dir(remote_dir_parent)
        local_repo_url = os.popen('git config --get remote.origin.url').read()
        if all([git_username, git_password]):
          local_repo_url = self.git_repo_http_pattern.sub(
            '\\1%s:%s@\\2' % (git_username, git_password), local_repo_url
            )
        elif git_username:
          local_repo_url = self.git_repo_http_pattern.sub(
            '\\1%s@\\2' % git_username, local_repo_url
            )
        elif git_password:
          logger.error('You must specify a git username as well as the password ...')
          sys.exit(1)
        local_repo_url_sanitized = local_repo_url.replace(str(git_password),'******')
        logger.info("Performing git clone from %s to %s ..." \
          % (local_repo_url_sanitized, self.remote_dir))
        cmd = 'git clone %s %s' % (local_repo_url.strip(), self.remote_dir)
        git_clone_result = self.remote_sub_process.call('/', cmd)
        if git_clone_result:
          rem_exists = True
        else:
          logger.error('Unable to remotely clone %s to remote path!' % local_repo_url_sanitized)
          sys.exit(1)
      else:
        if self.mk_remote_dir(self.remote_dir):
          logger.info("Performing initial sync to %s ..." % self.remote_dir)
          self.sftp_sync.to_remote(os.getcwd(), '%s/..' % self.remote_dir)
          rem_exists = True
        else:
          logger.error('Unable to create remote path!')
          sys.exit(1)                
    logger.info('Checking for locally changed files ...')
    if loc_is_git:
        # List modified and untracked files
        changed_cmd = '''git diff-index HEAD --name-status'''
        changed_files = [f.strip().split('\t')[1] for f in os.popen(changed_cmd).readlines() if not f.startswith('D\t')]
        untracked_cmd = '''git ls-files --others --exclude-standard'''
        untracked_files = [f.strip() for f in os.popen(untracked_cmd).readlines()]
        local_changed = changed_files + untracked_files
    else:
        # If local path is not a git repo then
        # we'll only sync files in the current working directory
        # that have changed within the last 5 minutes
        _dir = os.getcwd()
        exclusions = ['sftp-config.json']
        local_changed = list(fle for rt, _, f in os.walk(_dir) for fle in f if time.time() - os.stat(os.path.join(rt, fle)).st_mtime < 300 and f not in exclusions)
    logger.info('Checking for remotely changed files ...')
    sync_no_clobber = self.settings.get('sync_no_clobber')
    if rem_is_git:
        remote_changed_cmd = '''{} | awk '$1 != "D" {{print $2}}' && {}'''.format(changed_cmd, untracked_cmd)
        remote_changed = self.remote_sub_process.call(self.remote_dir, remote_changed_cmd)
        if remote_changed:
            if sync_no_clobber:
                to_sync = list(set(local_changed) - set(remote_changed))
            else:
                to_sync = list(set(local_changed))
        else:
            logger.error('There was a problem checking for remotely changed files')
            sys.exit(1)
    else:
        to_sync = list(set(local_changed))
    if len(to_sync) > 0:
        logger.info("Performing sync to %s ..." % self.remote_dir)
    for path in to_sync:
        dirname = os.path.dirname(path)
        filename = os.path.basename(path).strip()
        _file_path = os.path.join(dirname, filename)
        file_path = _file_path.replace('\\','/')
        _remote_path = os.path.join(self.remote_dir, file_path)
        remote_path = os.path.normpath(_remote_path).replace('\\','/')
        logger.debug('Syncing {} to remote {}'.format(file_path, remote_path))
        self.sftp_sync.to_remote(file_path, remote_path)    