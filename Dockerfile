# ----------------------------------
# Node build stage - build front end
FROM node:15.1 AS front

COPY ./front-app /front-app
WORKDIR /front-app

RUN npm install
# Creates the static web app  into the /front-app/build folder
RUN npm run build

# ----------------------------------
# Main build stage - backend + nginx to serve the frontend
FROM python:3.8-buster

# -------------- 1. setup nginx to serve frontend -----------------
RUN apt-get update -y && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    nginx

COPY --from=front /front-app/build /var/www/build

# Remove default nginx configs
RUN rm -f /etc/nginx/nginx.conf; rm -f /etc/nginx/sites-enabled/default

# Add our own (lightly modified) configs
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/nginx_mysite.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/nginx_mysite.conf /etc/nginx/sites-enabled/mysite

# Check that the configs are valid
RUN nginx -t


# -------------- 2. setup backend -----------------
COPY ./back /app
RUN pip install -r /app/requirements.txt
ENV PYTHONPATH="/app"

# ENV POSTGRES_PASSWORD=test - define password when starting
ENV DB_HOST=host.docker.internal
# Mount /app-data folders so that the container can access data
ENV DATA_DIR="/app-data/data"
ENV FILMS_DIR="/app-data/films"
ENV METADATA_DIR="/app-data/metadata"

RUN echo 'nginx; uvicorn app.main:app --host 127.0.0.1 --port 8080' >> /start.sh

CMD ["bash", "/start.sh"]
