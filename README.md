# Mooving IoT project


## Getting Started

1. Download and install on SD card latest Raspbian Buster Lite image:
    * [Raspbian Buster Lite.](https://www.raspberrypi.org/downloads/raspbian/)
    * [Install Raspbian Buster Lite on SD card using Etcher.](https://www.raspberrypi.org/documentation/installation/installing-images/)

2. Enable WIFI and SSH on Raspberry Pi:
    * [How to enable WIFI and SSH.](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md)

3. Connect to Raspberry Pi via SSH:
    * [More details about SSH on Raspberry Pi.](https://www.raspberrypi.org/documentation/remote-access/ssh/)

4. Enter commands to install Git client:

        sudo apt-get update
        sudo apt-get install git

5. Clone mooving-iot-firmware repository using Git client.

6. Move to the repository scripts folder:

        cd mooving-iot-firmware/scripts

7. Run setup script:

        sudo sh setup_project.sh

8. Generate ES256 encryption keys:

        sudo sh generate_keys.sh

9. Add device public key on Google Cloud IoT. To display the generated device public key, enter:

        sudo cat ../keys/ec_public.pem

10. Open file `run_project.sh` and change Google Cloud IoT details for the device to your own:

        CLOUD_REGION="region"
        PROJECT_ID="project_id"
        REGISTRY_ID="registry_id"
        DEVICE_ID="device_id"

11. Reboot device:

        sudo reboot

## License

This project is licensed under the License - see the [LICENSE.md](LICENSE.md) file for details.
