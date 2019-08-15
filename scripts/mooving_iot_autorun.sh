#!/bin/bash

### BEGIN INIT INFO
# Provides:          Mooving IoT
# Required-Start:    $local_fs $network $syslog
# Required-Stop:     $local_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Mooving IoT process
# Description:       Mooving IoT process
### END INIT INFO

# Run Mooving IoT process.
cd /home/pi/mooving-iot-firmware/scripts

# Start pigpiod service.
sudo pigpiod

while true
do
    sudo sh run_project.sh
done
