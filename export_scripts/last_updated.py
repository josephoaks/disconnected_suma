#!/usr/bin/env python3

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
channel_list = client.channel.listVendorChannels(key)

for channel in channel_list:
    raw_date = client.channel.software.getChannelLastBuildById(key, channel["id"])
    print(raw_date.split()[0] + " " + channel["label"])
