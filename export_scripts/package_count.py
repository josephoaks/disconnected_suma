#!/usr/bin/env python3

"""
Script Name: SUSE Manager channel package counter

Description: The purpose of this script is to grab the number of packages per channle as a
             quick way to compare to the remote server, ensuring the remote server does have
             the same amount.

             This script authenticates to SUSE Manager (SUMA) and retrieves the list of
             vendor channels along with the number of packages available in each. It
             requires credentials set in a configuration file located at /root/.mgr-sync. To
             create this file run `mgr-sync -s refresh` input the SUMA admin/password.

Usage:       Run this script directly with Python 3 interpreter on systems where SUMA client
             is configured. Ensure Python 3 and required libraries are installed.
"""

import os
import configparser
from xmlrpc.client import ServerProxy
import ssl
import socket

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
    return client, client.auth.login(manager_login, manager_password)

client, key = create_client()

# Collect vendor channel build date
if client and key:
    channel_list = client.channel.listVendorChannels(key)
    for channel in channel_list:
        raw_packages = client.channel.software.listAllPackages(key, channel["label"])
        pkg_count = len(raw_packages)
        print(f"{str(pkg_count).ljust(5)}\t{channel['label']}")
else:
    print("Failed to authenticate with SUSE Manager.")
