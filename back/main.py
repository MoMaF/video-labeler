from typing import Optional, List
import os
import glob
import json
import signal
import io

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, FileResponse, StreamingResponse
import pandas as pd
import cv2

from database_client import DatabaseClient
from models.cluster_labels import ClusterLabels

# Create web app and database connection
app = FastAPI()
db_client = DatabaseClient(
    user="admin",
    database="db",
    password=os.environ["DB_PASSWORD"],
)
signal.signal(signal.SIGINT, db_client.close)
signal.signal(signal.SIGTERM, db_client.close)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: move these to config
DATA_DIRS = [f"{os.environ['HOME']}/dev/facerec/data/*-data"]
FILMS_PATH = f"{os.environ['HOME']}/dev/facerec/films"
METADATA_DIR = f"{os.environ['HOME']}/dev/video-labels/metadata"

def read_metadata(metadata_dir):
    actors_path = os.path.join(metadata_dir, "actors.csv")
    df = pd.read_csv(actors_path)

    check_alnum = lambda c: str.isalnum(c) or c == " "
    strip_special = lambda s: ''.join(filter(check_alnum, s)).lower().strip()

    # Movie metadata
    movie_df = df[["movie_id", "movie_name", "movie_year"]] \
        .drop_duplicates("movie_id") \
        .set_index("movie_id") \
        .rename(columns={"movie_name": "name", "movie_year": "year"})
    movie_df["id"] = movie_df.index
    movie_df["basic_name"] = movie_df.name.apply(strip_special)
    movie_df = movie_df.sort_values(by="basic_name").drop(columns=["basic_name"])

    # Movie to actors map
    actors_df = df.set_index(["movie_id", "id"]).drop(columns="movie_name")
    actors_df["id"] = actors_df.index.get_level_values("id")
    valid_actor_ids = set(actors_df.index.get_level_values("id"))

    # Keep tabs on actor images in the backend
    images_path = os.path.join(metadata_dir, "actor_images")
    _, _, files = next(os.walk(images_path))
    actor_images_map = {}
    for image_file in files:
        # Filename like: actor-123-movie-876-5.jpeg
        basename = os.path.basename(image_file)
        parts = basename.split("-")
        if parts[0] == "actor" and int(parts[1]) in valid_actor_ids:
            actor_id = int(parts[1])
            if actor_id not in actor_images_map:
                actor_images_map[actor_id] = []
            actor_images_map[actor_id].append(basename)

    return movie_df, actors_df, actor_images_map

def img_tag(movie_id: int, frame: int, box: List[int]):
    """Get a 'standard' image tag as used by the face recognition stack.
    """
    # Real example: kept-121614:003616_235_183_293_262.jpeg
    return f"{movie_id}:{str(frame).zfill(6)}" + "_{}_{}_{}_{}".format(*box)

def read_datadirs(data_dirs):
    # Expand potential globs
    dirs = []
    for data_dir_path in data_dirs:
        dirs += glob.glob(data_dir_path)

    # Map movie ids to movie paths
    movie_path_map = {}
    _, _, movie_files = next(os.walk(FILMS_PATH))
    for name in movie_files:
        try:
            movie_id = int(name.split("-")[0])
            movie_path_map[movie_id] = os.path.join(FILMS_PATH, name)
        except:
            pass

    # Map id to directory data
    dir_data = {}
    for dir in dirs:
        movie_id = int(os.path.basename(dir).split("-")[0])
        trajectories_file = os.path.join(dir, "trajectories.jsonl")
        images_dir = os.path.join(dir, "images")

        _, _, images = next(os.walk(images_dir))
        images_set = set(images)

        with open(trajectories_file, "r") as f:
            trajectories = [json.loads(line) for line in f]
            # Filter trajectories to have only boxes that have an image.
            for t in trajectories:
                valid_boxes = []
                for frame, box in enumerate(t["bbs"], start=t["start"]):
                    file_name = f"kept-{img_tag(movie_id, frame, box)}.jpeg"
                    if file_name in images_set:
                        valid_boxes.append((frame, box))
                t["image_bbs"] = valid_boxes

        # Filter to valid:
        # trajectories = [t for t in trajectories if (len(t["image_bbs"]) > 5)]

        # Expect video file with the same name as directory (+ extension)
        assert movie_id in movie_path_map, f"Movie file not found for: {movie_id}"
        movie_path = movie_path_map[movie_id]

        data = {
            "id": movie_id,
            "path": dir,
            "movie_path": movie_path,
            "trajectories": trajectories,
            "n_trajectories": len(trajectories),
        }
        dir_data[movie_id] = data

    return dir_data

movie_df, actors_df, actor_images_map = read_metadata(METADATA_DIR)
valid_actor_ids = set(actors_df.index.get_level_values("id"))
dir_data = read_datadirs(DATA_DIRS)

# Filter movies to those that have data
movie_df = movie_df.loc[dir_data.keys()]
movie_df["year"] = movie_df.year.astype(int)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/movies")
def list_movies():
    json_str = movie_df.to_json(orient="records", force_ascii=False)
    return Response(content=json_str, media_type="application/json")

@app.get("/actors/{movie_id}")
def list_actors(movie_id: int):
    df = actors_df.loc[movie_id]
    actors = []
    for actor in df.itertuples():
        image_names = actor_images_map.get(actor.id, [])
        actors.append({
            "id": actor.id,
            "name": actor.name,
            "images": [f"images/{name}" for name in image_names],
        })
    return actors

@app.get("/frames/{movie_id}/{frame_index}.jpeg")
def get_frame(movie_id: int, frame_index: int):
    if not movie_id in dir_data:
        return HTTPException(404, f"No such movie {movie_id}.")

    cap = cv2.VideoCapture(dir_data[movie_id]["movie_path"])

    if not cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index):
        return HTTPException(400, "Bad request!")

    ret, frame = cap.read()

    if not ret:
        return HTTPException(500, "Error reading movie.")

    # Encode into jpeg in-memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
    result, encimg = cv2.imencode(".jpg", frame, encode_param)

    return StreamingResponse(io.BytesIO(encimg.tobytes()), media_type="image/jpeg")

@app.get("/images/actor-{actor_id}-movie-{remainder}.jpeg")
def get_image(actor_id: int, remainder: str):
    if actor_id not in valid_actor_ids:
        return HTTPException(404, f"Unknown actor id {actor_id}.")

    filename = f"actor-{actor_id}-movie-{remainder}.jpeg"
    file_path = os.path.join(METADATA_DIR, "actor_images", filename)

    if not os.path.exists(file_path):
        return HTTPException(404, f"File not found.")

    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )

@app.get("/images/{movie_id}:{label}.jpeg")
def get_image(movie_id: int, label: str):
    if movie_id not in movie_df.index:
        return HTTPException(404, f"Invalid movie id {movie_id}.")

    label = label.replace("/", "")
    movie_dir = dir_data[movie_id]["path"]
    file_name = f"kept-{movie_id}:{label}.jpeg"
    file_path = os.path.join(movie_dir, "images", file_name)

    if not os.path.exists(file_path):
        return HTTPException(404, f"File not found.")

    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )

@app.get("/faces/clusters/images/{movie_id}/{cluster_id}")
def get_cluster_images(movie_id: int, cluster_id: int):
    if movie_id not in movie_df.index:
        return HTTPException(404, f"Invalid movie id {movie_id}.")

    # Find potential labels for this cluster, in the database
    images_status = {}
    label = None
    annotation = db_client.get_annotations(movie_id, cluster_id)
    if annotation:
        images_status = {tag: (status == 1) for tag, status in annotation["images"]}
        label = annotation["label"]

    t = dir_data[movie_id]["trajectories"][cluster_id]
    image_urls = [
        f"images/{img_tag(movie_id, frame, box)}.jpeg"
        for frame, box in t["image_bbs"]
    ]

    images = []
    for frame, box in t["image_bbs"]:
        tag = img_tag(movie_id, frame, box)
        images.append({
            "url": f"images/{tag}.jpeg",
            "full_frame_url": f"frames/{movie_id}/{frame}.jpeg",
            "approved": images_status.get(tag, True),
            "frame_index": frame,
        })

    return {
        "cluster_id": cluster_id,
        "label": label,
        "images": images,
    }

@app.post("/faces/clusters/images/{movie_id}/{cluster_id}")
def set_cluster_labels(movie_id: int, cluster_id: int, data: ClusterLabels):
    # from images/{tag}.jpeg -> tag
    image_data = [(d.url[7:-5], int(d.approved)) for d in data.images]
    db_client.insert_annotations(movie_id, cluster_id, data.label, image_data)
    return {"status": "ok"}

@app.get("/faces/clusters/labels/{cluster_id}")
def get_cluster_labels(cluster_id: int):
    return {
        "cluster_id": cluster_id,
        "classes": [{"name": name, "id": i, "p": 0.54} for i, name in enumerate(SOME_NAMES)]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
