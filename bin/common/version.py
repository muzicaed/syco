#!/usr/bin/env python
'''
Control so one version of a command is only executed once on a server.

Example:
  SCRIPT_VERSION= 1
  try_
    # Mark the version of this script.
    version_obj = version.Version("installVersion", SCRIPT_VERSION)

    # Throw an exception if already executed on this host.
    version_obj.check_executed()

    # Do some code, that should only be executed once on this server.

    version_obj.mark_executed()
  except Exception, e
    print(e)

'''

__author__ = "daniel.lindh@cybercow.se"
__copyright__ = "Copyright 2011, The System Console project"
__maintainer__ = "Daniel Lindh"
__email__ = "syco@cybercow.se"
__credits__ = ["???"]
__license__ = "???"
__version__ = "1.0.0"
__status__ = "Production"

import ConfigParser
import socket

import app

class VersionException(Exception):
  '''
  Raised for Version exceptions
  '''

class Version:
  hostname = socket.gethostname()

  command = None
  version = None

  config_file_name = app.SYCO_ETC_PATH + "version.cfg"

  def __init__(self, command, version):
    self.command = command
    self.version = version

  def check_executed(self):
    '''
    Check if the command has been executed, raise Exception otherwise.

    '''
    if (app.options.force == 0 and self.is_executed()):
      raise VersionException("Command " + str(self.command) + " version " + str(self.version) + " is already executed")

  def mark_executed(self):
    '''
    Mark that a specific command/routine/script with a specific
    version has been executed on the current server.

    '''
    self._set_version(self.version)

  def mark_uninstalled(self):
    '''
    Mark that a specific command/routine/script with a verion 0, which means
    that the command has not been executed on the current server.

    '''
    self._set_version(0)

  def is_executed(self):
    '''
    Check if a specific command/routine/script with a specific
    version has been executed on the current server.

    '''
    config = ConfigParser.RawConfigParser()
    config.read(self.config_file_name)

    if config.has_section(self.hostname):
      if config.has_option(self.hostname, self.command):
        if config.get(self.hostname, self.command) == self.version:
          return True
    return False

  def _set_version(self, version):
    '''
    Set version to version config file.

    '''
    config = ConfigParser.RawConfigParser()
    config.read(self.config_file_name)

    if not config.has_section(self.hostname):
      config.add_section(self.hostname)

    config.set(self.hostname, self.command, version)
    config_file = open(self.config_file_name, 'wb')
    config.write(config_file)
    config_file.close()
