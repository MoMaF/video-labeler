# Deployment

Instructions for how to deploy the `video-labeler` tool to run as an internet-accessible service. For running locally during development, see [this guide](./README.md) instead.

Before you start you need:

- A remote Linux VM that you can access over `ssh` or similar. All commands listed will be run in this VM. This guide assumes Ubuntu 20.
- The VM firewall should allow traffic on port `443`, for HTTPS.
- You need to know the external IP or domain of the VM.

This guide will cover:

1. Gettings HTTPS certificates using [Let's Encrypt](https://letsencrypt.org/).
2. Adding simple users accounts with `htpasswd`
3. How to build/start the docker containers used by the `video-labeler`

___

## 1. HTTPS

All commands run in your Linux VM. Note: this requires port 80 (HTTP) to be accessible, and not blocked by the firewall.

To use Let's Encrypt, the VM needs to have a domain name. Only an IP address is not enough. Find your domain name using:

```
dig -x <vm_public_ip_address_here>
```

Next, we'll get the certificates using `certbot`.

```
# Update snap
sudo snap install core; sudo snap refresh core

# Install certbot
sudo snap install --classic certbot

# Link binary
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Assuming that the VM public domain is "my-cool-vm.example.com"
sudo certbot certonly --standalone --preferred-challenges http -d my-cool-vm.example.com

# Check that certificates were created
ls -l /etc/letsencrypt/live/my-cool-vm.example.com
# Should print something like this:
README
cert.pem -> ../../archive/my-cool-vm.example.com/cert1.pem
chain.pem -> ../../archive/my-cool-vm.example.com/chain1.pem
fullchain.pem -> ../../archive/my-cool-vm.example.com/fullchain1.pem
privkey.pem -> ../../archive/my-cool-vm.example.com/privkey1.pem
```

Also, generate Diffie Hellman key exchange params:

```
openssl dhparam -out dhparam.pem 4096
```

We're done for now. We'll come back to these generated files later.

## 2. Create user accounts

How to create user accounts for annotators that want to use `video-labeler` from the browser.

All commands run in your Linux VM. Note: this is NOT an advanced password management system, and doesn't try to be. It will only serve as a basic authentication system for a small deployment.

`video-labeler` uses HTTPBasicAuth for this.

```
# Install htpasswd
sudo apt install apache2-utils

# Add all users with passwords, into a file named .htpasswd
htpasswd -bc .htpasswd username1 mycoolpassword1
htpasswd -b .htpasswd username2 mycoolpassword2
htpasswd -b .htpasswd username3 mycoolpassword3

# Check that the file is ok
cat .htpasswd
# username1:$apr1$tjVk1/vr$5xCIswBWhhjQYp/H3Negp/
# username2:$apr1$cYTdOarw$7fLiBtKLQTt.mW1/Ko8Op/
# username3:$apr1$OMJdBN9U$QLI4fRY/WbUVLagVK3Py80
```

Keep track of the `.htpasswd` file; we'll come back to it soon.

## 3. Build docker images

All commands run in your Linux VM.

Install docker using [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04).

```
# Check that installation is valid, should look like this...
sudo systemctl status docker

● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2021-02-25 13:24:42 UTC; 16s ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 15167 (dockerd)
      Tasks: 8
     Memory: 53.2M
     CGroup: /system.slice/docker.service
             └─15167 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
```

Clone this `video-labeler` repo, and build the docker images. Note: whenever the software is updated, you'll have to pull and build again.

```
git clone git@github.com:MoMaF/video-labeler.git ; cd video-labeler

# 1. Build backend image (this can take a while)
sudo docker build -t video-labeler .

# 2. Build database image
cd back/database
sudo docker build -t postgresql .

# 3. Create a local docker network, that the backend will use to connect to the database
sudo docker network create net1
```

## 4. Setup folder structure, and run containers

All commands run in your Linux VM.

The backend (docker container) will want to read lots of data when it starts, so we need to setup a data folder that contains everything it needs. This guide assumes that everything is collected in a folder called:

- `/media/volume`

**Steps:**

1. Get movie data from [`facerec`](https://github.com/MoMaF/facerec), a single sample can be found here: [113528-data.zip](https://drive.google.com/file/d/1g7LW2DR1ASJUh-jzznSNUqS2__yut9Uu/view?usp=sharing).

Put the extracted data into a data root at `/media/volume/data`. The sample folder would then have the full path `/media/volume/data/113528-data`

2. Put raw video files into `/media/volume/data/films`.

This is needed if you want to show full frames, during labeling. The files should begin with the movie id, like `113528-Tuntematon-1955.mp4`.

3. Get metadata (images, info) about actors. Sample here: [`metadata.zip`](https://drive.google.com/file/d/1K9p_fiLbMooNMCRjEWktg_M4CVg1vMua/view?usp=sharing).

Put the extracted metadata folder at: `/media/volume/metadata`

4. Put the HTTPS-related files into `/media/volume/tls`

Copy/move the files as follows:

```
../my-cool-vm.example.com/cert1.pem --> /media/volume/tls/cert.pem
../my-cool-vm.example.com/privkey1.pem --> /media/volume/tls/privkey.pem
../my-cool-vm.example.com/fullchain1.pem --> /media/volume/tls/fullchain.pem
dhparam.pem --> /media/volume/tls/dhparam.pem
```

5. Create a folder where the database can store its binary data: `/media/volume/postgres-data`

6. Move `.htpasswd` to `/media/volume/.htpasswd`


**Now, start the containers:**

For instance, they can be run in separate `screen`s.

```
# 1. Start database before the backend
# Set your own password instead of pick_a_better_password_here (!!!)
sudo docker run -it \
    --network net1 \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=pick_a_better_password_here \
    -v /media/volume/postgres-data:/var/lib/postgresql/data \
    --name db \
    postgresql:latest

# 2. Find database ip (within net1) with docker inspect
sudo docker inspect db

# 3. Start backend
# Assuming database container local IP 172.18.0.2
sudo docker run -it \
    --network net1 \
    -e DB_PASSWORD=pick_a_better_password_here \
    -e DB_HOST=172.18.0.2 \
    -v /media/volume/data:/app-data/data \
    -v /media/volume/films:/app-data/films \
    -v /media/volume/metadata:/app-data/metadata \
    -v /media/volume/tls:/etc/ssl/certs \
    -v /media/volume/.htpasswd:/etc/nginx/.htpasswd \
    -p 443:443 \
    --name labeler \
    video-labeler:latest
```

That's it!

You should now be able to access the software by going to https://my-cool-vm.example.com
