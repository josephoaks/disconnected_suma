#!/usr/bin/env python3

"""
Description: This script is used for the initial export of channels for the
             customer. This means if they are new to SUMA, or an existing
             user and we don't know when they got their last update from the
             SCC, or they are getting a new channel for i.e. a new Service Pack.

             This script automates the process of exporting channel data from a
             specified channel, by choosing which parent channel to export,
             and optionally exporting individual child channels.

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
    try:
        key = client.auth.login(manager_login, manager_password)
        return client, key
    except Fault as e:
        print(f"Error logging in: {e}")
        exit(1)

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
                parent_child_map[channel["label"]] = []
        return parent_child_map
    except Fault as e:
        print(f"Error fetching channel hierarchy: {e}")
        exit(1)

def user_selection(parent_child_map):
    print("Is this a new parent or a new child channel?")
    print("1. New Parent Channel")
    print("2. New Child Channel")
    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == '1':
        print("Select a parent channel to export:")
        parents = list(parent_child_map.keys())
        for i, parent in enumerate(parents, start=1):
            print(f"{i}. {parent}")
        while True:
            try:
                parent_choice = int(input("Enter the number of the parent channel: ")) - 1
                if 0 <= parent_choice < len(parents):
                    return [(parents[parent_choice], None)]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    elif choice == '2':
        print("Select the parent channel for the new child:")
        parents = list(parent_child_map.keys())
        for i, parent in enumerate(parents, start=1):
            print(f"{i}. {parent}")
        while True:
            try:
                parent_choice = int(input("Enter the number of the parent channel: ")) - 1
                if 0 <= parent_choice < len(parents):
                    selected_parent = parents[parent_choice]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        print(f"Select a child channel under {selected_parent}:")
        children = parent_child_map[selected_parent]
        for i, child in enumerate(children, start=1):
            print(f"{i}. {child}")
        while True:
            try:
                child_choice = int(input("Enter the number of the child channel: ")) - 1
                if 0 <= child_choice < len(children):
                    return [(selected_parent, children[child_choice])]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    else:
        print("Invalid choice. Please restart the script and choose 1 or 2.")
        exit(1)

def export_channel(client, key, channel, output_dir, log_file_path, options_str, packages_only_after=None):
    os.makedirs(output_dir, exist_ok=True)
    command = f"inter-server-sync export --channels='{channel}' --outputDir='{output_dir}' {options_str}"
    if packages_only_after:
        command += f" --packagesOnlyAfter='{packages_only_after}'"
    result = subprocess.run(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Error during export of {channel}: {result.stderr.decode('utf-8')}")
    # Log to file
    with open(log_file_path, "a") as log_file:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        log_file.write(f"{current_time} Export for channel {channel} completed.\n")

def main():
    setup_directories()
    log_file_path = setup_logging()
    client, key = create_client()
    parent_child_map = channel_hierarchy(client, key)
    selected_channels = user_selection(parent_child_map)
    options_str = command_options(COMMON_OPTIONS)

    for parent, child in selected_channels:
        if child:
            export_channel(client, key, child, os.path.join(UPDATES_DIR, child), log_file_path, options_str)
        else:
            export_channel(client, key, parent, os.path.join(INITIAL_DIR, parent), log_file_path, options_str, FIXED_DATE.strftime('%Y-%m-%d'))
            for child_channel in parent_child_map[parent]:
                export_channel(client, key, child_channel, os.path.join(UPDATES_DIR, child_channel), log_file_path, options_str)

    subprocess.run(['chown', '-R', f'{RSYNC_USER}.{RSYNC_GROUP}', BASE_DIR], check=True)
    total_time = datetime.datetime.now() - datetime.datetime.strptime(TODAY, "%Y-%m-%d")
    with open(log_file_path, "a") as log_file:
        log_file.write(f"Total execution time: {total_time}\n")

if __name__ == "__main__":
    main()
