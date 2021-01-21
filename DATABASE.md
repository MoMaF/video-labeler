# Running the database locally

This is about running `video-labeler` locally, **for development purposes**.

The easiest way to launch a local PostgreSQL database for the `video-labeler` is using Docker. The instructions for this can be found below.

Using Docker for this is not required, of course. Any local PostgreSQL setup that adheres to the database/schema requirements will do.

### Setting up the PostgreSQL container

After running the commands seen here, your PostgreSQL setup is done, and the `video-labeler` backend will be able to connect. Kill the container at any time using CTRL-C. Omit `sudo` if using macOS.

Commands:

```
# 1. Build image
cd back/database
sudo docker build -t postgresql .

# 2. Create & start container
# Replace /data/path/on/host with any folder on your host machine!
sudo docker run -it \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=test \
    -v /data/path/on/host:/var/lib/postgresql/data \
    --name db \
    postgresql:latest
```

### Extra: rerunning after closing

The previous step created a container named `db`. After the container was killed, it can be restarted the next time using:

```
sudo docker start db
```

And killed again using:

```
sudo docker stop db
```
