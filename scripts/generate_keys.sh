#!/bin/sh

# Generate device ES256 key pair.
sudo yes | rm -r ../keys
sudo mkdir ../keys
sudo openssl ecparam -genkey -name prime256v1 -noout -out ../keys/ec_private.pem
sudo openssl ec -in ../keys/ec_private.pem -pubout -out ../keys/ec_public.pem
