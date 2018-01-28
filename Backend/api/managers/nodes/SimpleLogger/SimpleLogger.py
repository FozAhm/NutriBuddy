import sys, argparse, datetime, logging, traceback
import json

class SimpleLogger:

    def __init__(self, service_name, verbosity=3):
        self.starttime = '{:%d-%m-%y_%H:%M:%S}'.format(datetime.datetime.now())
        # logging.basicConfig(level=logging.DEBUG)
        self.format_string = '%(levelname)s: %(message)s'
        self.log_file_name = 'logs/' + service_name + '{:%d-%m-%y_%H-%M-%S}'.format(datetime.datetime.now()) + '.log'
        self.dump_format = "\n%s\n%s\n%s\n\n\n\n\n"
        self.json_dump_indent = 4
        self.demarcation = "*=_=*=_=*=_=*=_=*=_=*=_=*=_=*=_=*=_=*=_=*"
        self.log_level = logging.INFO
        if verbosity == 0:
            self.log_level = logging.CRITICAL
        elif verbosity == 1:
            self.log_level = logging.ERROR
        elif verbosity == 2:
            self.log_level = logging.WARNING
        elif verbosity == 3:
            self.log_level = logging.INFO
        elif verbosity == 4:
            self.log_level = logging.DEBUG
        elif verbosity == 5:
            self.log_level = logging.DEBUG
        # logging.basicConfig(format=self.format_string, filename=self.log_file_name, level=self.log_level)
        logging.basicConfig(format=self.format_string, level=self.log_level)
        # logging.info('Started %s at %s' % (service_name, self.starttime))

    def critical(self, output):
        logging.critical(output)
    
    def error(self, output):
        logging.error(output)
    
    def warning(self, output):
        logging.error(output)
    
    def info(self, output):
        logging.info(output)

    def debug(self, output):
        # print 'DEBUG PRINT: ' + output
        logging.debug(output)

    def dump_var(self, variable):
        if type(variable) is str:
            return variable
        elif type(variable) is int:
            return str(variable)
        elif type(variable) is long:
            return str(variable)
        elif type(variable) is float:
            return str(variable)
        elif type(variable) is tuple:
            return variable
        elif type(variable) is list:
            # return str(variable)
            return json.dumps(variable, indent=self.json_dump_indent, sort_keys=False)
        elif type(variable) is dict:
            return json.dumps(variable, indent=self.json_dump_indent, sort_keys=False)
        else:
            try:
                return json.dumps(variable, indent=self.json_dump_indent, sort_keys=False)  # TODO: May have to change this to just return str(variable)
            except Exception as exc:
                logging.warn('Failed to dump variable.')
                message = 'Couldn\'t dump variable (type not handled by helper function dump_var?)'
                return message

    def dump_exception(self, exc):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # exc_string = str(exc)
        # exc_string = traceback.format_exc().splitlines()
        exc_string = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        # exc_string = repr(traceback.extract_tb(exc_traceback))
        print ('DEBUG PRINT: Exception occurred. See logs at %s for more information.' % self.log_file_name)
        logging.exception('Exception likely caused by error with this traceback:\n') # NOTE: If this code is ever converted to Python 3, calling this here instead of in the `except Exception as exc:` block may result in unexpected output