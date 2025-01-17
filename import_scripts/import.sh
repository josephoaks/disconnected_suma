
#!/bin/bash

# Script Name: import_sync.sh
#
# Description: This script synchronizes files from a remote server using rsync,
#              then processes the directories to perform specific import tasks.
#              It reads configurations from a YAML file to retrieve host details
#              and other necessary credentials.
#
# Usage: ./import_sync.sh
#
# YAML Configuration Requirements:
#   - host: The hostname or IP address of the remote server.
#   - pass: The password for the XML-RPC user.
#
# Example YAML Content:
# ---
# version: 2
# host: example.com
# uname: org_name
# pass: yourpassword
#
# Notes: Ensure the YAML file 'import.yaml' is located in the same
#        directory as this script. Requires rsync, SSH access, and permissions
#        to read the specified directories.

# Change the directory where the script resides for cron execution
cd "$(dirname "$0")" || exit 1

# Set variables
yaml_file="./import.yaml"
if [ ! -f "$yaml_file" ]; then
    echo "Configuration file not found: $yaml_file"
    exit 1
fi
host=$(awk '/^host:/ { print $2 }' "$yaml_file")
uname=$(awk '/^uname:/ { print $2 }' "$yaml_file")
pass=$(awk '/^pass:/ { print $2 }' "$yaml_file")
basedir='/mnt/import'
log_dir="/mnt/logs"
log_file="${log_dir}/$(date +"%Y-%m-%d")-import.log"
rsync_log="${log_dir}/$(date +"%Y-%m-%d")-rsync.log"

if [ ! -d "$log_dir" ]; then
  mkdir -p "$log_dir"
fi

log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$log_file"
}

# Updates system using zypper
update_system() {
  log "Checking for system updates."
  zypper ref
  zypper -n update
}

# Clear source directory before rsync of new data.
cleanup() {
  log "Cleaning up directories."
  rm -rf "$basedir"/updates/*
  rm -rf "$basedir"/initial/*
}

update_system
cleanup

# SSH Configuration variables.
ssh_user='rsyncuser'
ssh_key="id_rsa"
ssh_options="-i /home/${ssh_user}/.ssh/${ssh_key}"
rsync -avP -e "ssh ${ssh_options}" "${ssh_user}@${host}":/ "$basedir" >> "$rsync_log" 2>&1

process_directory() {
  if [ -z "$(find "$1" -mindepth 1 -type d -print -quit)" ]; then
    dir_name=$(basename "$1")
    log "No imports at this time for $dir_name."
    return
  fi

  local options="--xmlRpcUser=$uname --xmlRpcPassword=$pass --logLevel=error"
  for dir in "$1"/*; do
    if [ -d "$dir" ]; then
      inter-server-sync import --importDir="$dir" $options >> "$log_file" 2>&1
      log "Import for directory $dir completed."
    fi
  done
}

process_directory "$basedir/updates"
process_directory "$basedir/initial"
