# Brickmaster2 Config File Progressor

import adafruit_logging as logging
import sys
import json
import os
import board

# from pprint import pformat
# import json


class BM2Config:
    def __init__(self, config_file=None):
        self._config = None
        self._config_file = None
        self._logger = logging.getLogger("BrickMaster2")
        # If we're running under Circuitpython, we *must* have the config.json in a specific place.
        if sys.implementation.name == 'circuitpython':
            print("Running on Circuitpython, using config.json directly.")
            self._config_file = 'config.json'
        elif os.uname().sysname.lower() == 'linux':
            print("Running on general-purpose Linux, checking system paths...")
            # Otherwise, add support for locating the search path.
            global Path
            from pathlib import Path
            self._search_paths = [Path.cwd().joinpath('config.json')]
            # If config file was provided, insert it to the beginning of the search path.
            if config_file is not None:
                self._search_paths.insert(0, Path(config_file))
        else:
            print("Unidentified platform, not supported. Cannot continue.\n\tOS System Name: {}"
                  "\n\tPython Implementation: {}".format(os.uname().sysname, sys.implementation.name))
        self.process_config()
        self._logger.info("Setting log level to: {}".format(self._config['system']['log_level_name']))
        self._logger.setLevel(self._config['system']['log_level'])

    def process_config(self):
        self._logger.info("Processing config.")
        if sys.implementation.name != 'circuitpython':
            # Now try to find the config file.
            for path in self._search_paths:
                try:
                    self.config_file = path
                except TypeError:
                    self._logger.info("Rejecting config path {}, value isn't a string or path".format(path))
                except ValueError:
                    self._logger.info("Rejecting config path {}, value isn't an actual, accessible file.".format(path))
            if self._config_file is None:
                raise ValueError("Cannot find valid config file! Attempted: {}".format(self._search_paths))
        self.load_config()

    @property
    def config_file(self):
        # Only one option with Circuitpython.
        if sys.implementation.name == 'circuitpython':
            return 'config.json'
        else:
            if self._config_file is None:
                return None
            else:
                return str(self._config_file)

    @config_file.setter
    def config_file(self, the_input):
        if sys.implementation.name == 'circuitpython':
            pass
        else:
            # IF a string, convert to a path.
            if isinstance(the_input, str):
                the_input = Path(the_input)
            if not isinstance(the_input, Path):
                # If it's not a Path now, we can't use this.
                raise TypeError("Config file must be either a string or a Path object.")
            if not the_input.is_file():
                raise ValueError("Provided config file {} is not actually a file!".format(the_input))
            # If we haven't trapped yet, assign it.
            self._config_file = the_input

    def load_config(self,):
        # Open the current config file and suck it into a staging variable.
        self._config = self._open_json(self.config_file)
        self._logger.debug("Read config JSON:")
        self._logger.debug(json.dumps(self._config))
        if not self._validate():
            self._logger.critical("Could not validate configuration! Cannot continue.")
            sys.exit(1)
        else:
            self._logger.info("Config file validated.")

    # Method for opening loading a JSON file and slurping it in.
    @staticmethod
    def _open_json(config_path):
        with open(config_path, 'r') as config_file_handle:
            # Need to do a try except here to actully test for valid JSON.
            the_json = json.load(config_file_handle)
        return the_json

    # Validation methods.

    # Master validator
    def _validate(self):
        # Check for the required config sections.
        required_keys = ['system', 'controls', 'scripts']
        for key in required_keys:
            self._logger.debug("Checking for section '{}'".format(key))
            if key not in self._config:
                self._logger.critical("Required configuration section '{}' not present. Cannot continue!".format(key))
                sys.exit(1)
        # Make sure the right sections exist.
        self._validate_system()
        # Validate the secrets and merge into the main system config.
        self._validate_secrets()
        # Validate the controls.
        self._validate_controls()
        # Validate the displays.
        self._validate_displays()
        # Validate the scripts.
        self._validate_scripts()
        self._logger.debug("Have script config: {}".format(self._config['scripts']))
        return True

    # Validate system settings
    def _validate_system(self):
        self._logger.debug("Validating system section")
        required_keys = ['name']
        optional_keys = ['log_level', 'secrets', 'ntp_server', 'tz']
        optional_defaults = {
            'log_level': 'info',
            'secrets': 'secrets.json',
            'ntp_server': None,
            'tz': 'Etc/UTC'
        }
        # Check for presence of required options.
        for key in required_keys:
            self._logger.debug("Checking for required key '{}'".format(key))
            if key not in self._config['system']:
                self._logger.critical("Required config option '{}' missing. Cannot continue!")
                sys.exit(0)
        # Check for optional settings, assign the defaults if need be.
        for key in optional_keys:
            self._logger.debug("Checking for optional key '{}'".format(key))
            if key not in self._config['system']:
                self._logger.warning("Option '{}' not found, using default '{}'".format(key, optional_defaults[key]))
                self._config['system'][key] = optional_defaults[key]
        # Map the log level to an actual Logging entity.
        if self._config['system']['log_level'].lower() == 'debug':
            self._config['system']['log_level_name'] = 'debug'
            self._config['system']['log_level'] = logging.DEBUG
        elif self._config['system']['log_level'].lower() == 'info':
            self._config['system']['log_level_name'] = 'info'
            self._config['system']['log_level'] = logging.INFO
        elif self._config['system']['log_level'].lower() == 'warning':
            self._config['system']['log_level_name'] = 'warning'
            self._config['system']['log_level'] = logging.WARNING
        elif self._config['system']['log_level'].lower() == 'error':
            self._config['system']['log_level_name'] = 'error'
            self._config['system']['log_level'] = logging.ERROR
        elif self._config['system']['log_level'].lower() == 'CRITICAL':
            self._config['system']['log_level_name'] = 'error'
            self._config['system']['log_level'] = logging.INFO
        else:
            self._config['system']['log_level_name'] = 'info'
            self._config['system']['log_level'] = logging.INFO


    def _validate_secrets(self):
        self._logger.debug("Integrating secrets.")
        self._config['secrets'] = {}
        required_keys = ['broker', 'mqtt_username', 'mqtt_password']
        # Systems with a full OS handle their own networking. CircuitPython boards need us to handle the network.
        # In the latter case, SSID and passphrase are required
        if os.uname().sysname.lower() != "linux":
            required_keys.append("SSID")
            required_keys.append("password")
        optional_keys = ['port']
        optional_defaults = {'port': 1883 }

        # Open the secrets file.
        secrets = self._open_json(self._config['system']['secrets'])
        self._logger.debug("Got secrets: {}".format(json.dumps(secrets)))
        # Check for presence of required options.
        for key in required_keys:
            self._logger.debug("Checking for required key '{}'".format(key))
            if key not in secrets:
                self._logger.critical("Required config option '{}' missing. Cannot continue!".format(key))
                sys.exit(0)
            else:
                self._config['secrets'][key] = secrets[key]
        # Check for optional settings, assign the defaults if need be.
        for key in optional_keys:
            self._logger.debug("Checking for optional key '{}'".format(key))
            if key not in secrets:
                self._logger.warning("Option '{}' not found, using default '{}'".format(key, optional_defaults[key]))
                self._config['secrets'][key] = optional_defaults[key]

    def _validate_controls(self):
        if not isinstance(self._config['controls'], list):
            self._logger.critical('Controls not correctly defined. Must be a list of dictionaries.')
            return
        i = 0
        to_delete = []
        while i < len(self._config['controls']):
            required_keys = ['name', 'type']
            for key in required_keys:
                self._logger.debug("Checking for required control key '{}'".format(key))
                if key not in self._config['controls'][i]:
                    self._logger.critical("Required control config option '{}' missing in control {}. Cannot continue!".
                                          format(key, i))
                    to_delete.append(i)
                    i += 1
                    continue
            # Pull out control type, this just make it easier.
            ctrltype = self._config['controls'][i]['type']
            if ctrltype == 'gpio':
                if 'pin' not in self._config['controls'][i]:
                    self._logger.error("Cannot set up control '{}', no 'pin' directive.".
                                       format(self._config['controls'][i]['name']))
                    to_delete.append(i)
                    i += 1
                    continue
            else:
                self._logger.error("Cannot set up control '{}', type '{}' is not supported.".format(i, ctrltype))
                to_delete.append(i)
                i += 1
                continue
            i += 1
        # Delete any controls that have been invalidated
        for d in sorted(to_delete, reverse=True):
            self._logger.debug("Deleting control '{}'".format(d))
            del self._config['controls'][d]

    # Validate the displays on loading.
    def _validate_displays(self):
        if not isinstance(self._config['displays'], list):
            self._logger.critical('Displays not correctly defined. Must be a list of dictionaries.')
            return
        i = 0
        to_delete = []
        while i < len(self._config['displays']):
            self._logger.debug("Checking display {}. Has raw config {}".format(i, self._config['displays'][i]))
            required_keys = ['name', 'type', 'address']
            for key in required_keys:
                self._logger.debug("Checking for required display key '{}'".format(key))
                if key not in self._config['displays'][i]:
                    self._logger.critical("Required control display option '{}' missing in display {}. Discarding display.".
                                          format(key, i))
                    to_delete.append(i)
                    i += 1
                    continue
            # Make sure type is legitimate.
            if self._config['displays'][i]['type'].lower() not in ('seg7x4', 'bigseg7x4'):
                self._logger.critical("Display type '{}' not known in display {}. Discarding display.".
                                      format(self._config['displays'][i]['type'], i))
                to_delete.append(i)
                i += 1
                continue
            # Convert the address to a hex value.
            try:
                self._config['displays'][i]['address'] = int(self._config['displays'][i]['address'], 16)
            except TypeError:
                self._logger.critical("Address not a string for display {}. Should be in \"0xXX\" format. "
                                      "Discarding display.".format(i))
                i += 1
                to_delete.append(i)
                continue
            # Default when_idle to blank, if not otherwise specified.
            if 'idle' not in self._config['displays'][i]:
                self._config['displays'][i]['idle'] = {'show': 'blank'}
            else:
                # If the idle was put in as a string, convert it into a dict and default to full brightness.
                if isinstance(self._config['displays'][i]['idle'], str):
                    self._config['displays'][i]['idle'] = {
                        'show': self._config['displays'][i]['idle'],
                        'brightness': 1
                         }
                else:
                    # Check the show option.
                    if self._config['displays'][i]['idle']['show'] not in ('time','date','blank'):
                        self._logger.warning("Specified idle value for display {} ('{}') not valid. Defaulting to blank.".
                                         format(i, self._config['displays'][i]['idle']['show']))
                        self._config['displays'][i]['idle']['show'] = 'blank'
                        self._config['displays'][i]['idle']['brightness'] = 1

                    # Convert the brightness setting to a float.
                    try:
                        self._config['displays'][i]['idle']['brightness'] = float(self._config['displays'][i]['idle']['brightness'])
                    except KeyError:
                        self._config['displays'][i]['idle']['brightness'] = 1
                    except ValueError:
                        self._config['displays'][i]['idle']['brightness'] = 1
            i += 1

        # Delete any invalidated displays
        self._logger.debug("Displays to delete: {}".format(to_delete))
        for d in sorted(to_delete, reverse=True):
            self._logger.debug("Deleting display '{}'".format(d))
            del self._config['displays'][d]

    # Validate the scripts.
    def _validate_scripts(self):
        if not isinstance(self._config['scripts'], dict):
            self._logger.critical('Scripts not correctly defined. Must be a dictionary.')
            return
        i = 0
        # Can we scan the scripts directory?
        # If we're not on linux, absolutely not! CircuitPython doesn't support Pathlib and scanning.

        if os.uname().sysname != 'linux':
            self._logger.warning("Cannot scan scripts directory. Scripts must be individually enumerated.")
        elif 'scan_dir' in self._config['scripts']:
            # Scan_dir setting, use that, convert it to a proper bool.
            if self._config['scripts']['scan_dir'].lower() == 'true':
                self._config['scripts']['scan_dir'] = True
            else:
                self._config['scripts']['scan_dir'] = False
        else:
            # Scan_dir not included, default it to True since we're on linux.
            self._config['scripts']['scan_dir'] = True

        # If files isn't explicitly defined, make it an empty list.
        if 'files' not in self._config['scripts']:
            self._config['scripts']['files'] = []

    # Get the complete network config.
    @property
    def system(self):
        return_dict = {
            'name': self._config['system']['name'],

            'broker': self._config['secrets']['broker'],
            'port': self._config['secrets']['port'],
            'mqtt_username': self._config['secrets']['mqtt_username'],
            'mqtt_password': self._config['secrets']['mqtt_password'],
            'ntp_server': self._config['system']['ntp_server'],
            'tz': self._config['system']['tz']
        }
        # On a microcontroller, we have to handle the network. On a general-purpose OS, it does that work for us.
        if os.uname().sysname.lower() != "linux":
            return_dict['SSID'] =  self._config['secrets']['SSID']
            return_dict['password'] = self._config['secrets']['password']
        return return_dict

    # Controls config. No merging of data required here.
    @property
    def controls(self):
        return self._config['controls']

    # Displays were already validated, return them when asked.
    @property
    def displays(self):
        return self._config['displays']

    @property
    def scripts(self):
        return self._config['scripts']
