FROM postgres:13

#
# Example run:
# docker run --name db -p 5432:5432 -e POSTGRES_PASSWORD=test postgresql:latest
#

# ENV POSTGRES_PASSWORD=test - define password when starting
ENV POSTGRES_USER=admin
ENV POSTGRES_DB=db
# Mount PGDATA to the host computer when running container.
ENV PGDATA=/var/lib/postgresql/data

COPY ./create.sql /docker-entrypoint-initdb.d/
