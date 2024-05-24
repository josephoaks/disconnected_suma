#!/bin/bash

# Function to check and install Git if it's not installed
install_git() {
  if ! git --version &>/dev/null; then
    echo "Git is not installed. Attempting to install using Zypper..."
    zypper install -y git-core
    if [ $? -eq 0 ]; then
      echo "Git has been successfully installed."
    else
      echo "Failed to install Git."
      exit 1
    fi
  else
    echo "Git is already installed."
  fi
}

# Function to clone a Git repository
clone_repository() {
  local repo_url=$1
  local target_dir=$2
  git clone $repo_url $target_dir
  if [ $? -eq 0 ]; then
    echo "Repository cloned successfully into $target_dir."
  else
    echo "Failed to clone the repository."
    exit 1
  fi
}

# Function to organize files and directories
organize_files() {
  local target_dir=$1
  # Create directory trees
  mkdir -p /mnt/logs
  mkdir -p /mnt/export/{initial,updates,scripts}

  # Copy files to their respective directories
  cp -a "${target_dir}/export_scripts/." /mnt/scripts/
  cp -a "${target_dir}/import_scripts/." /mnt/export/scripts/

  # Set execute bits conditionally
  find /mnt/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \;
  find /mnt/export/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \;

  # Set ownership
  chown -R rsyncuser.users /mnt/export
}

# Function to update configuration file
update_config() {
  local config_file="${target_dir}/import_scripts/import.yaml"

  # Ask user for details
  echo "Please enter the new configuration details:"
  read -p "Enter host: " host
  read -p "Enter username: " uname
  echo -e "Enter password: \c"  # Prompt for the password
  read -rs password
  echo  # Move to a new line after the password input

  # Debugging: Confirm what's being read (remove in production)
  #echo "Debug: Password to be written is: '$password'"

  # Using awk to update the YAML file safely, ensuring special characters in password are handled
  awk -v host="$host" -v uname="$uname" -v pass="$password" '
    /^host:/ {$0 = "host: " host}
    /^uname:/ {$0 = "uname: " uname}
    /^pass:/ {$0 = "pass: " pass}
    {print}
  ' "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"


  echo "Configuration updated successfully in $config_file"
}

# Main function to orchestrate script actions
main() {
  if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root. Please run again with 'sudo' or as the root user."
    exit 1
  fi

  install_git

  local repo_url="https://github.com/josephoaks/disconnected_suma"
  local target_dir="$HOME/disconnected_suma"

  clone_repository $repo_url $target_dir
  update_config
  organize_files $target_dir

  rm -rf "$target_dir"
}

# Run the main function
main
