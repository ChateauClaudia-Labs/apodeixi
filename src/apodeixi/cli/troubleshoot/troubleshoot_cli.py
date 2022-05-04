# Purpose of this Python module is to serve as an entry point to debug a problematic CLI command

import sys                                              as _sys
import os                                               as _os
from click.testing                                      import CliRunner

from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.cli.apo_cli                               import apo_cli

# Type here the command  and CLI you want to run, as a list of the string tokens comprising the CLI command
#

BR_FILENAME                                 = "Astrea.modernization.big-rocks.journeys.a6i.xlsx"

COMMAND                                     = ["post", BR_FILENAME]
COMMAND                                     = ["get", "form", "milestone.journeys.a6i", "cicloquimica.production", "modernization"]
CLI                                         = apo_cli

# Select the environment you want to troubleshoot
#
APODEIXI_ROOT                               = "C:/Users/aleja/Documents/Code/chateauclaudia-labs/a6i_repos/"
_os.environ["APODEIXI_CONFIG_DIRECTORY"]    = APODEIXI_ROOT + "/UAT_ENV"

# Select the working folder where you want to work
#
WORKING_FOLDER                              = APODEIXI_ROOT + "/UAT_ENV/collaboration_area/journeys/FY 22/Astrea/Official"

_os.chdir(WORKING_FOLDER)

def troubleshoot_command():

    root_trace                  = FunctionalTrace(parent_trace=None, path_mask=None) .doing("Troubleshooting") 

    runner = CliRunner()
    result                      = runner.invoke(CLI, COMMAND)

    if result.exit_code != 0:
        raise ApodeixiError(root_trace, "CLI command failed",
                            data = {"CLI exit code":    str(result.exit_code),
                                    "CLI exception":    str(result.exc_info),
                                    "CLI output":       str(result.output),
                                    "CLI traceback":    str(result.exc_info)})
    return

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        troubleshoot_command()

    main(_sys.argv)