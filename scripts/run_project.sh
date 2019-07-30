#!/bin/bash

# Google Cloud IoT details.
CLOUD_REGION="europe-west1"
PROJECT_ID="open-iot-development"
REGISTRY_ID="test_001"
DEVICE_ID="test"

# Run Mooving IoT process.
cd ..
sudo python3 -m mooving_iot --project_id $PROJECT_ID --registry_id $REGISTRY_ID --device_id $DEVICE_ID --cloud_region $CLOUD_REGION
