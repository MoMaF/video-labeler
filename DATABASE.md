# Running the database locally

This is about running `video-labeler` locally, **for development purposes**.

The easiest way to launch a local PostgreSQL database for the `video-labeler` is using Docker. The instructions for this can be found below.

Using Docker for this is not required, of course. Any local PostgreSQL setup that adheres to the database/schema requirements will do.

### Build the database Docker image

```
# Omit sudo if using macOS
cd back/database
sudo docker build -t postgresql .
```

### Run the Docker image

After running the command below, your PostgreSQL setup is done, and the `video-labeler` backend will be able to connect. Kill the container using CTRL-C.

```
# Omit sudo if using macOS
sudo docker run -it \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=test \
    -v "${HOME}/dev/video-labels/db-data":/var/lib/postgresql/data \
    --name db \
    postgresql:latest
```

### Rerunning after closing

The previous step created a container named `db`. After the container was killed, it can be restarted the next time using:

```
sudo docker start db
```

And killed again using:

```
sudo docker stop db
```
