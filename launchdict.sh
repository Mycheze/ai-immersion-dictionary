#!/bin/bash
# Root launcher script that calls the more comprehensive launch script in scripts directory

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Call the main launcher script
"$SCRIPT_DIR/scripts/launch_dictionary.sh" "$@"
