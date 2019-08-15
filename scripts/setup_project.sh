#!/bin/sh

# Set device time zone: UTC.
sudo timedatectl set-timezone UTC

# Update package lists.
sudo apt-get update
sudo yes | apt-get install software-properties-common

sudo add-apt-repository universe
sudo apt-get update

# Install python 3 and pip.
sudo yes | apt-get install python3
sudo yes | apt-get install python3-pip

# Install python external dependencies.
sudo yes | pip3 install -r ../requirements.txt

# Install pigpio service.
sudo yes | sudo apt-get install pigpio python3-pigpio

# Install openssl.
sudo yes | apt-get install openssl

# Add project to autorun on device startup.
sudo cp mooving_iot_autorun.sh /etc/init.d/
cd /etc/init.d
sudo chmod +x mooving_iot_autorun.sh
sudo update-rc.d mooving_iot_autorun.sh defaults

# Enable I2C1 peripheral module.
sudo raspi-config nonint do_i2c 0
