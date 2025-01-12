#!/usr/bin/env python3

"""
Description: This script is used for the initial export of channels for the
             customer. This means if they are a new to SUMA, or an existing
             user and we don't know when they got their last update from the
             SCC, or they are getting a new channel for i.e. a new Service Pack.

             This script automates the process of exporting channel data from a
             specified channel, by choosing which parent channle to export,
             then clearing the directory before use, and handling file and user
             permissions.

             The script logs each export operation to a daily log file and
             changes the ownership of the exported files to a specific user and
             group.

Constants:
             BASE_DIR - Base directory from which channels are exported.
             RSYNC_USER - Username owning the exported files.
             RSYNC_GROUP - Group owning the exported files.
             LOG_DIR - Directory where logs are stored.
             TODAY - Today's date, used for naming the log file.

Instructions:
             1. THIS SCRIPT REQUIRES THE USE OF THE mgr-sync -s refresh
                CREDENTIALS FILE!
             2. Ensure paths for BASE_DIR, and LOG_DIR, are correctly set 
                according to your system configuration.
             3. Adjust RSYNC_USER and RSYNC_GROUP to match appropriate user
                and group on your system.
             4. Run this script with sufficient permissions to access and modify
                the specified directories and files.
"""


import os
import shutil
import datetime
import subprocess
import configparser
import ssl
import socket
from xmlrpc.client import ServerProxy, Fault
import shlex

# Constants
BASE_DIR = "/mnt"
INITIAL_DIR = os.path.join(BASE_DIR, "export/initial")
UPDATES_DIR = os.path.join(BASE_DIR, "export/updates")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
RSYNC_USER = "rsyncuser"
RSYNC_GROUP = "users"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")
FIXED_DATE = datetime.date(2050, 1, 1)  # Fixed 'packagesOnlyAfter' date
COMMON_OPTIONS = {'orgLimit': '2', 'logLevel': 'error'}  # Common options for export commands

def setup_directories():
    os.makedirs(LOG_DIR, exist_ok=True)
    shutil.rmtree(INITIAL_DIR, ignore_errors=True)
    os.makedirs(INITIAL_DIR, exist_ok=True)
    shutil.rmtree(UPDATES_DIR, ignore_errors=True)
    os.makedirs(UPDATES_DIR, exist_ok=True)

def setup_logging():
    log_file_path = os.path.join(LOG_DIR, f"{TODAY}-combined-export.log")
    return log_file_path

def create_client():
    config_path = os.path.expanduser('/root/.mgr-sync')
    config = configparser.ConfigParser()
    with open(config_path, 'r') as f:
        config.read_string('[DEFAULT]\n' + f.read())
    manager_login = config.get('DEFAULT', 'mgrsync.user')
    manager_password = config.get('DEFAULT', 'mgrsync.password')
    suma_fqdn = socket.getfqdn()
    manager_url = f"https://{suma_fqdn}/rpc/api"
    context = ssl.create_default_context()
    client = ServerProxy(manager_url, context=context)
    key = client.auth.login(manager_login, manager_password)
    return client, key

def command_options(options_dict):
    """Generate command line options string from dictionary."""
    return ' '.join([f"--{opt}='{val}'" for opt, val in options_dict.items()])

def channel_hierarchy(client, key):
    try:
        channels = client.channel.listVendorChannels(key)
        parent_child_map = {}
        for channel in channels:
            details = client.channel.software.getDetails(key, channel["label"])
            parent_label = details.get('parent_channel_label')
            if parent_label:
                if parent_label not in parent_child_map:
                    parent_child_map[parent_label] = []
                parent_child_map[parent_label].append(channel["label"])
            else:
                parent_child_map[channel["label"]] = []  # Parent with no children listed as an empty list
        return parent_child_map
    except Fault as e:
        print(f"Error fetching channel hierarchy: {e}")
        exit(1)

def user_select_parent(parent_child_map):
    parents = list(parent_child_map.keys())
    selected_parents = []
    print("Please select a parent channel to export (Enter 0 when done):")
    for i, parent in enumerate(parents, start=1):
        print(f"{i}. {parent}")
    while True:
        try:
            choice = int(input("Enter your choice: ")) - 1
            if choice == -1:
                break
            if 0 <= choice < len(parents):
                selected_parents.append(parents[choice])
                print(f"Selected {parents[choice]}. Add more or press 0 to continue.")
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Please enter a valid integer.")
    return selected_parents

def export_initial(client, key, parent_child_map, selected_parents, log_file_path):
    options_str = command_options(COMMON_OPTIONS)
    date_str = FIXED_DATE.strftime('%Y-%m-%d')
    for parent in selected_parents:
        initial_dir = os.path.join(INITIAL_DIR, parent)
        os.makedirs(initial_dir, exist_ok=True)
        initial_export_command = f"inter-server-sync export --channel-with-children='{parent}' --outputDir='{initial_dir}' {options_str} --packagesOnlyAfter='{date_str}'"
        result = subprocess.run(shlex.split(initial_export_command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error during export of {parent}: {result.stderr.decode('utf-8')}")
        # Log to file
        with open(log_file_path, "a") as log_file:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            log_file.write(f"{current_time} Initial export for channel {parent} completed.\n")

def export_updates(client, key, parent_child_map, selected_parents, log_file_path):
    options_str = command_options(COMMON_OPTIONS)
    for parent in selected_parents:
        channels_to_export = [parent] + parent_child_map[parent]  # Include parent and its children
        for channel in channels_to_export:
            update_dir = os.path.join(UPDATES_DIR, channel)
            os.makedirs(update_dir, exist_ok=True)
            update_export_command = f"inter-server-sync export --channels='{channel}' --outputDir='{update_dir}' {options_str}"
            result = subprocess.run(shlex.split(update_export_command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                print(f"Error during export of {channel}: {result.stderr.decode('utf-8')}")
            # Log to file
            with open(log_file_path, "a") as log_file:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                log_file.write(f"{current_time} Updates export for channel {channel} completed.\n")

def main():
    setup_directories()
    log_file_path = setup_logging()
    client, key = create_client()
    parent_child_map = channel_hierarchy(client, key)
    selected_parents = user_select_parent(parent_child_map)
    export_initial(client, key, parent_child_map, selected_parents, log_file_path)
    export_updates(client, key, parent_child_map, selected_parents, log_file_path)
    # Change ownership of the base directory recursively
    subprocess.run(['chown', '-R', f'{RSYNC_USER}.{RSYNC_GROUP}', BASE_DIR], check=True)
    # Calculate total time and log
    end_time = datetime.datetime.now()
    total_time = end_time - datetime.datetime.strptime(TODAY, "%Y-%m-%d")
    with open(log_file_path, "a") as log_file:
        log_file.write(f"Total execution time: {total_time}\n")
    client.auth.logout(key)

if __name__ == "__main__":
    main()
