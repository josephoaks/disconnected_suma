#!/usr/bin/env python3

"""
Description: 
              This script is used to manage channels on a SUMA server.
              It reads channel names from a 'channels.txt' file, adds
              them using 'mgr-sync' without synchronization until all
              channels are added and then syncs the selected channels.

Instructions:
             1. Define your channels.txt file path
             2. Set the list of channels to sync, one line per channel.
             3. chmod +x channels_sync.py and execute
"""

import os
import subprocess

# Define the path to the channels file
channels_file = "channels.txt"

# Check if the channels file exists
if not os.path.isfile(channels_file):
    print("Error: channels.txt file not found.")
    exit(1)

# Open and read the channels file
with open(channels_file, 'r') as file:
    for line in file:
        channel_name = line.strip()

        if channel_name:
            subprocess.run(['mgr-sync', 'add', 'channel', channel_name, '--no-sync'])

# Sync channels from the SCC
subprocess.run(['mgr-sync', 'refresh', '--refresh-channels'])
