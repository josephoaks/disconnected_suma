#!/usr/bin/env python3

"""
Description:
             This script facilitates the management and monitoring of software 
             channels on a SUSE Manager server. It logs into the server using 
             XML-RPC, fetches the current version of the SUSE Manager, lists 
             vendor channels, and retrieves the last build date of each channel.
             The results, including the SUSE Manager version and channel 
             updates, are saved to a text file to be used in setting up a server
             for use in a "Disconnect" or "Air-gapped" environment.

Usage:
             1. Ensure Python 3 is installed on your system.
             2. Place this script in an appropriate directory and ensure it is 
                executable.
             3. Create/Modify the '/root/.mgr-sync'.
                mgr-sync -s refresh
             4. Run the script using the command:
                $ ./this_script_name.py
             5. Check the 'suma_info.txt' file for output after execution.

"""

import os
import re
import requests
import socket
import ssl
import configparser
from xmlrpc.client import ServerProxy

# Disable SSL warnings due to verify=False
requests.packages.urllib3.disable_warnings()

# Function to create the XML-RPC client and login
def create_client():
    config_path = os.path.expanduser('/root/.mgr-sync')
    config = configparser.ConfigParser()
    with open(config_path, 'r') as f:
         config.read_string('[DEFAULT]\n' + f.read())
    MANAGER_LOGIN = config.get('DEFAULT', 'mgrsync.user')
    MANAGER_PASSWORD = config.get('DEFAULT', 'mgrsync.password')
    SUMA_FQDN = socket.getfqdn()
    MANAGER_URL = f"https://{SUMA_FQDN}/rpc/api"
    context = ssl.create_default_context()
    client = ServerProxy(MANAGER_URL, context=context)
    key = client.auth.login(MANAGER_LOGIN, MANAGER_PASSWORD)
    return client, key, MANAGER_URL

# Get the client, session key, and URL from create_client
client, key, MANAGER_URL = create_client()

# Fetch the SUSE Manager version using requests
response = requests.get(MANAGER_URL.replace("/rpc/api", ""), verify=False)
version = "Unknown"
if response.status_code == 200:
    version_pattern = r"webVersion: '(\d+\.\d+\.\d+)'"
    match = re.search(version_pattern, response.text)
    if match:
        version = match.group(1)

# Fetch channel updates info
channel_list = client.channel.listVendorChannels(key)
channel_updates_info = []
for channel in channel_list:
    raw_date = client.channel.software.getChannelLastBuildById(key, channel["id"])
    formatted_date = raw_date.split()[0]
    channel_updates_info.append(f"{formatted_date} {channel['label']}")

# Log out after operations
client.auth.logout(key)

# Write information to a file
with open("suma_info.txt", "w") as file:
    file.write("SUSE Manager Information\n\n")
    file.write(f"SUSE Manager version: {version}\n\n")
    file.write("List of Product Channels:\n")
    file.write("\n".join([info.split()[1] for info in channel_updates_info]))
    file.write("\n\nProduct Channel Last Update:\n")
    file.write("\n".join(channel_updates_info))
