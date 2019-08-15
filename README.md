# Project Title

Mooving IoT project.

## Getting Started

1. Download and install on SD card latest Raspbian Buster Lite image:
    * [Raspbian Buster Lite.](https://www.raspberrypi.org/downloads/raspbian/)
    * [Install Raspbian Buster Lite on SD card using Etcher.](https://www.raspberrypi.org/documentation/installation/installing-images/)

2. Enable Linux console output via UART. Open the file `config.txt` on SD card and write at the end:

        enable_uart=1

    * [More details about UART on Raspberry Pi.](https://www.raspberrypi.org/documentation/configuration/uart.md)

3. Connect USB to UART bridge to Raspberry Pi pin header. Open UART terminal (Tera Term or Putty) on PC. UART configuration:

        baudrate: 115200, no parity, 1 stop bit

    When boot procedure is finished enter default user credentials:

        login: pi
        password: raspberry

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

11. Run script to start Mooving IoT process:

        sudo sh run_project.sh

    or reboot device:

        sudo reboot

## License

This project is licensed under the License - see the [LICENSE.md](LICENSE.md) file for details.
