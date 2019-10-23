#!/bin/bash

# Google Cloud IoT details.
CLOUD_REGION=""
PROJECT_ID=""
REGISTRY_ID=""
DEVICE_ID=""

# Run Mooving IoT process.
cd ..
sudo python3 -m mooving_iot --project_id $PROJECT_ID --registry_id $REGISTRY_ID --device_id $DEVICE_ID --cloud_region $CLOUD_REGION
