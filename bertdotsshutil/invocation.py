from bertdotsshutil.logger import Logger
import os
import sys

# Import third-party and custom modules
try:
    from bertdotssh.dictutils import Struct
except ImportError as e:
    print('Error in %s ' % os.path.basename(self_file_name))
    print('Failed to import at least one required module')
    print('Error was %s' % e)
    print('Please install/update the required modules:')
    print('pip install -U -r requirements.txt')
    sys.exit(1)

# Setup Logging
logger = Logger().init_logger(__name__)

class RemoteCliInvocation:

    def __init__(self, settings, client):

        self.settings = settings
        self.ssh = client
        self.logger = logger

    def call(self, dirname, cmd, stdout_listen=False):

        base_cmd = """
cd {};

""".format(dirname.replace('\\', '/'))
        remote_cmd = base_cmd + cmd
        if stdout_listen:
            stdin, stdout, stderr = self.ssh.execute(remote_cmd, stream_stdout=stdout_listen)
            exit_code = stdout.channel.recv_exit_status()
            cli_result = {
            'stdout' : [l.strip() for l in stdout],
            'stderr' : [l.strip() for l in stderr],
            'returncode': exit_code
            }
            return Struct(cli_result)
        else:
            stdin, stdout, stderr = self.ssh.execute(remote_cmd)
            exit_code = stdout.channel.recv_exit_status()
            stdout = stdout.readlines() or "None"
            stderr = stderr.readlines() or "None"
            if exit_code == 0:
                return [l.strip() for l in stdout]
            else:
                self.logger.error('Remote command failed with error {}: {}'.format(exit_code,stderr))
                return False