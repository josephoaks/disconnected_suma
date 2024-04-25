#! /usr/bin/env python3

"""
Script Description:
                    This script is designed to connect to a SUSE Manager server,
                    authenticate using credentials stored in a local configuration file, 
                    and retrieve the last build dates of all vendor channels managed by
                    the server. It outputs these dates along with the respective channel
                    labels. This is useful for administrators needing to track software
                    channel updates.

Usage:
                    Ensure the SUSE Manager login credentials are correctly set in the 
                    ~/.mgr-sync file. Run this script directly from the command line in 
                    a Unix-like environment with Python 3 installed:
                    $ ./name_of_script.py

Ensure that this script has executable permissions:
$ chmod +x last_update.py
"""

import os
import subprocess
from xmlrpc.client import ServerProxy
import ssl
import socket

config_file_path = os.path.expanduser("/root/.mgr-sync")
login_command = f"awk -F' = ' '$1==\"mgrsync.user\" {{print $2}}' {config_file_path}"
password_command = f"awk -F' = ' '$1==\"mgrsync.password\" {{print $2}}' {config_file_path}"

# Information needed to access and authenticate to SUSE Manager
SUMA_FQDN = socket.getfqdn()
MANAGER_LOGIN = subprocess.check_output(login_command, shell=True).decode().strip()
MANAGER_PASSWORD = subprocess.check_output(password_command, shell=True).decode().strip()

MANAGER_URL = "https://" + SUMA_FQDN + "/rpc/api"

# Connect and log in to SUSE Manager using SSL
context = ssl.create_default_context()
client = ServerProxy(MANAGER_URL, context=context)
key = client.auth.login(MANAGER_LOGIN, MANAGER_PASSWORD)

# Collect vendor channel build date
channel_list = client.channel.listVendorChannels(key)

for channel in channel_list:
    raw_date = client.channel.software.getChannelLastBuildById(key, channel["id"])
    print(raw_date.split()[0] + " " + channel["label"])
