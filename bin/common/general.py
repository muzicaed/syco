#!/usr/bin/env python
'''
General python functions that don't fit in it's own file.

'''

__author__ = "daniel.lindh@cybercow.se"
__copyright__ = "Copyright 2011, The System Console project"
__maintainer__ = "Daniel Lindh"
__email__ = "syco@cybercow.se"
__credits__ = ["???"]
__license__ = "???"
__version__ = "1.0.0"
__status__ = "Production"

import glob
import os
import re
import shutil
import stat
import string
import inspect
import subprocess
import time
import sys
from random import choice
from socket import *

import app
import expect
import pexpect

def remove_file(path):
  '''
  Remove file(s) in path, can use wildcard.

  Example
  remove_file('/var/log/libvirt/qemu/%s.log*')

  '''
  for file_name in glob.glob(path):
    app.print_verbose('Remove file %s' % file_name)
    os.remove('%s' % file_name)

def grep(file_name, pattern):
  '''
  Return true if regexp pattern is included in the file.

  '''
  prog = re.compile(pattern)
  for line in open(file_name):
    if prog.search(line):
      return True
  return False

def delete_install_dir():
  '''
  Delete the folder where installation files are stored during installation.

  '''
  if (os.access(app.INSTALL_DIR, os.W_OK | os.X_OK)):
    app.print_verbose("Delete " + app.INSTALL_DIR + " used during installation.")
    shutil.rmtree(app.INSTALL_DIR, ignore_errors=True)
    os.chdir("/tmp")

def create_install_dir():
  '''
  Create folder where installation files are stored during installation.

  It could be files downloaded with wget, like rpms or tar.gz files, that should
  be installed.

  '''
  import atexit

  if (not os.access(app.INSTALL_DIR, os.W_OK | os.X_OK)):
    app.print_verbose("Create install dir " + app.INSTALL_DIR + " to use during installation.")
    os.makedirs(app.INSTALL_DIR)
    atexit.register(delete_install_dir)

  if (os.access(app.INSTALL_DIR, os.W_OK | os.X_OK)):
    os.chmod(app.INSTALL_DIR, stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
    os.chdir(app.INSTALL_DIR)
  else:
    raise Exception("Can't create install dir.")

def download_file(src, dst=None, user="", remote_user=None, remote_password=None):
  '''
  Download a file using wget, and place in the installation tmp folder.

  download_file("http://www.example.com/file.gz", "file.gz")

  '''
  app.print_verbose("Download: " + src)
  if (not dst):
    dst = os.path.basename(src)

  create_install_dir()
  if (not os.access(app.INSTALL_DIR + dst, os.F_OK)):
    cmd = "-O " + app.INSTALL_DIR + dst
    if (remote_user):
      cmd += " --user=" + remote_user

    if (remote_password):
      cmd += " --password=\"" + remote_password + "\""

    shell_exec("wget " + cmd + " " + src, user=user)
    # Looks like the file is not flushed to disk immediatley,
    # making the script not able to read the file immediatley after it's
    # downloaded. A sleep fixes this.
    time.sleep(2)

  if (not os.access(app.INSTALL_DIR + dst, os.F_OK)):
    raise Exception("Couldn't download: " + dst)

def generate_password(length=8, chars=string.letters + string.digits):
  '''Generate a random password'''
  return ''.join([choice(chars) for i in range(length)])

def is_server_alive(server, port):
  '''
  Check if port on a server is responding, this assumes the server is alive.

  '''
  try:
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(5)
    result = s.connect_ex((server, int(port)))
  finally:
    s.close()

  if (result == 0):
    return True
  return False

def wait_for_server_to_start(server, port):
  '''
  Wait until a network port is opened.

  '''
  app.print_verbose("\nWait until " + str(server) + " on port " + str(port) + " starts.", new_line=False)
  while(not is_server_alive(server, port)):
    app.print_verbose(".", new_line=False, enable_caption=False)
    time.sleep(5)
  app.print_verbose(".")

def shell_exec(command, user="", cwd=None, events=None, output=True):
  '''
  Execute a shell command using pexpect, and writing verbose affected output.

  '''
  # Build command to execute
  args=[]
  if (user):
    args.append(user)
  args.append('-c ' + command)

  if (output):
    app.print_verbose("Command: su " + user + " -c '" + command + "'")

  # Setting default events
  if events is None:
      events = {}

  events["Verify the SYCO master password:"] = app.get_master_password

  keys = events.keys()
  value = events.values()

  num_of_events = len(keys)

  # Timeout for ssh.expect
  keys.append(pexpect.TIMEOUT)

  # When ssh.expect reaches the end of file. Probably never
  # does, is probably reaching [PEXPECT]# first.
  keys.append(pexpect.EOF)

  # Set current working directory
  if (cwd == None):
    cwd = os.getcwd()

  out = expect.spawn("su", args, cwd=cwd)

  if (not output):
    out.disable_output()

  if (output):
    app.print_verbose("---- Result ----", 2)
  stdout = ""
  index = 0
  while (index < num_of_events+1):
    index = out.expect(keys, timeout=3600)
    stdout += out.before

    if index >= 0 and index < num_of_events:
      if (inspect.isfunction(value[index])):
        out.send(str(value[index]())  + "\n")
      else:
        out.send(value[index])
    elif index == num_of_events:
      app.print_error("Catched a timeout from pexpect.expect, lets try again.")

  if (out.exitstatus and output):
    app.print_error("Invalid exitstatus %d" % out.exitstatus)

  if (out.signalstatus and output):
    app.print_error("Invalid signalstatus %d - %s" % out.signalstatus, out.status)

  # An extra line break for the looks.
  if (output and stdout and app.options.verbose >= 2):
    print("\n"),

  out.close()

  return stdout

def shell_run(command, user="root", cwd=None, events={}):
  '''
  Execute a shell command using pexpect.run, and writing verbose affected output.

  Use shell_exec if possible.

  #TODO: Try to replace this with shell_exec

  '''
  command = "su " + user + ' -c "' + command + '"'

  # Need by Ubuntu when doing SU.
  #if (user != ""):
  #  user_password = app.get_user_password(user)
  #  events["(?i)Password: "] = user_password + "\n"

  # Set current working directory
  if (cwd == None):
    cwd = os.getcwd()

  app.print_verbose("Command: " + command)
  (stdout, exit_status) = pexpect.run(command,
    cwd=cwd,
    events=events,
    withexitstatus=True,
    timeout=10000
  )

  app.print_verbose("---- Result (" + str(exit_status) + ")----", 2)
  app.print_verbose(stdout, 2)

  if (exit_status == None):
    raise Exception("Couldnt execute " + command)

  return stdout

def set_config_property(file_name, search_exp, replace_exp):
  '''
  Change or add a config property to a specific value.

  #TODO: Optimize, do more then one change in the file at the same time.

  '''
  if os.path.exists(file_name):
    exist = False
    try:
      shutil.copyfile(file_name, file_name + ".bak")
      r = open(file_name + ".bak", 'r')
      w = open(file_name, 'w')
      for line in r:
        if re.search(search_exp, line):
          line = re.sub(search_exp, replace_exp, line)
          exist = True
        w.write(line)

      if exist == False:
        w.write(replace_exp + "\n")
    finally:
      r.close()
      w.close()
      os.remove(file_name + ".bak")
  else:
    w = open(file_name, 'w')
    w.write(replace_exp + "\n")
    w.close()

# TODO: Set a good name.
def set_config_property2(file_name, replace_exp):
  search_exp = r".*" + re.escape(replace_exp) + r".*"
  set_config_property(file_name, search_exp, replace_exp)

if __name__ == "__main__":
  command = 'echo "moo"'
  command = command.replace('\\', '\\\\')
  command = command.replace('"', r'\"')
  command = 'su -c"' + command + '"'
  print command
  print shell_exec(command)

  download_file("http://airadvice.com/buildingblog/wp-content/uploads/2010/05/hal-9000.jpg")
  os.chdir("/tmp/install")
  print shell_exec("ls -alvh")