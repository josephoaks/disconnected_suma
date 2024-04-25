# Disconnected SUSE Manager (air-gapped environment)

## Overview

These scripts are provided to ease the export and import of SUSE Manager Product Channels.
SUSE Manager connects to the SUSE Customer Center to pull down updates using Organizational
Credentials, for a "Disconntected" or "Air-gapped" environment that can not reach the SCC, 
no updates can be retrieved. As such the `inter-server-sync` package can be used to export
channels from one SUMA server and import on another.

## Description

Export
  - initial_export.py
      This file is used for initial export or when putting a new channel on to the disconnected
      server.
  - last_update_export.py
      This file is used for daily exports, by checking the API to retrieve the channel list,
      then checking the API for the ChannelLastBuildById to determine if it has been updated
      todays date or the previous date (this can be adjusted if say the target server was
      offline and not received several days of updates)
  - channels_sync.py
      This file is used mainly incases where you take an existing SUMA server and move it
      behind a DMZ where it will no longer connect directly to the SCC at which point you can
      get a list of channels `spacewalk-remove-channel -l > channels.txt` and use that file
      to build a new server with those channels.
  - package_count.py
      This file is used as a quick way from the CLI to get a package count to compare the
      two servers together to make sure they are in sync, run it on both servers and compare.

Import
  - import.sh
      Main import script, this will parse the data retrieved from the host server, either
      an initial or daily update and import that data.
  - last_update.py
      This file is used to determine via the API when the last time the channels were synced
      with the SCC or updated via the import.
  - package_count.py
      Same as the above
  - suma_info.py
      This file will retrieve basic data to help in the setup of a new SUMA server based on
      an existing server.
 
## Requirement

- `zypper in -y spacewalk-utils*`
- `zypper in -y inter-server-sync`
- Python 3.x
- Bash 4.x
- rsync 3.x
- rsyncuser created with ssh key set without a password for automation

## Usage

Step 1. User Createion

First thing to do is setup an `rsyncuser` on both servers, us an SSH key without a password
for automation. On the target server create the SSH key, on the host server add the key
to the ~rsyncuser/.ssh/authorized_keys file

Step 2. File structure

The default setup assumes `/mnt/import` and `/mnt/export` to be NFS/SAN mount so as not
to fill up primary drives, this can be adusted in the scripts to meet any directory
path you choose.

The exports can be quite massive for an initial export, that said, look at the drive
usage for the `/var/spacewalk` and add at least 10% more for the `/mnt/export` and 
`/mnt/import` due to the fact this will export all the packages and a sql export.

Daily exports from the `last_update_export.py` are designed to be much much smaller
by checking the API to determine if a channel had updates today or yesterday and only
export the channel if it did, if not then that channel is skipped. This makes the 
exports smaller making the data transerfer times shorter and the imports much faster.

Step 3. Logging

By default logging is setup to get in `/mnt/logs` for both the import and export servers.
These are daily log files that do not take up much space but it is recommended to clear
them out at least monthly.

Step 4. Execution

Initial Export:
 ```
 ./initial_export.py    # all scripts have script headers
```

 Daily Export:
 ```
 ./last_update_export.py
```
 it is recommended to run this via cron
 ```
 0 0 * * * /usr/bin/python3 /path/to/last_update_export.py
```

 Import:
 `./import.sh` # run this manually once to make sure all works before setting cron
it is recommended to run this via cron at least 2 hours behind the export cron to
ensure the export is completed.
```
0 2 * * * /bin/bash /path/to/import.sh
```






