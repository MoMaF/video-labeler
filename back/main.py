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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In a cluster, how many images to show for each trajectory (max)
ITEMS_PER_TRAJECTORY = 2

# Send predictions to frontend if probability is above this
PREDICTION_MIN_P = 0.40

# TODO: move these to config
DATA_DIRS = [os.environ["DATA_DIRS"]]
FILMS_DIR = os.environ["FILMS_DIR"]
METADATA_DIR = os.environ["METADATA_DIR"]

def read_metadata(metadata_dir):
    # actors.csv contains data about movies, and which actors where in them.
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

    # actor_images.csv links images to actors (and movies)
    # Columns: index,actor_id,movie_id,filename
    actor_images_path = os.path.join(metadata_dir, "actor_images.csv")
    actor_images_df = pd.read_csv(actor_images_path, index_col="actor_id").sort_index()

    return movie_df, actors_df, actor_images_df

def img_tag(movie_id: int, frame: int, box: List[int]):
    """Get a 'standard' image tag as used by the face recognition stack.
    """
    # Real example: kept-121614:003616_235_183_293_262.jpeg
    return f"{movie_id}:{str(frame).zfill(6)}" + "_{}_{}_{}_{}".format(*box)

def split_evenly(items, split_n: int):
    """Select evenly distributed split-n items from a list.
    """
    n = len(items)
    if split_n >= n:
        return items
    step = n // (split_n - 1)
    return [items[min(n - 1, m)] for m in range(0, n + step - 1, step)][:split_n]

def read_datadirs(data_dirs):
    # Expand potential globs
    dirs = []
    for data_dir_path in data_dirs:
        dirs += glob.glob(data_dir_path)

    # Map movie ids to movie paths
    movie_path_map = {}
    _, _, movie_files = next(os.walk(FILMS_DIR))
    for name in sorted(movie_files):
        try:
            movie_id = int(name.split("-")[0])
            movie_path_map[movie_id] = os.path.join(FILMS_DIR, name)
        except:
            pass

    # Map id to directory data
    dir_data = {}
    for dir in dirs:
        movie_id = int(os.path.basename(dir).split("-")[0])
        trajectories_file = os.path.join(dir, "trajectories.jsonl")
        clusters_file = os.path.join(dir, "clusters.json")
        predictions_file = os.path.join(dir, "predictions.json")
        images_dir = os.path.join(dir, "images")

        _, _, images = next(os.walk(images_dir))
        images_set = set(images)

        # Read all trajectories for this movie
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

        # Read clusters corresponing to each trajectory
        with open(clusters_file, "r") as f:
            cluster_indices = json.load(f)["clusters"]
            assert len(cluster_indices) == len(trajectories), "All trajectories need a cluster!"

        # Compute better image lookup table for clusters
        # Note: trajectories are implicitly indexed by their order in the list
        # Cluster indices are assumed to be dense, from zero
        clusters = {}
        for ti, ci in enumerate(cluster_indices):
            if ci not in clusters:
                clusters[ci] = {
                    "image_data": [],
                    "n_trajectories": 0,
                    "n_shown_images": 0,  # N images that will be send to the frontend
                    "n_total_images": 0,  # Total images in related trajectories
                }
            trajectory = trajectories[ti]
            # TODO: smarter selection of images to show?
            image_bbs = split_evenly(trajectory["image_bbs"], ITEMS_PER_TRAJECTORY)
            # Tuples in the list are: (trajectory_id, frame_index, bounding_box)
            clusters[ci]["image_data"] += [(ti, *ib) for ib in image_bbs]
            clusters[ci]["n_shown_images"] = len(clusters[ci]["image_data"])
            clusters[ci]["n_total_images"] += len(trajectory["image_bbs"])
            clusters[ci]["n_trajectories"] += 1

        # Read per-cluster predictions
        with open(predictions_file, "r") as f:
            predictions = json.load(f)
            # Convert keys to integers (JSON only has string keys)
            predictions = {
                int(cluster_id): {int(actor_id): p for actor_id, p in cluster_preds.items()}
                for cluster_id, cluster_preds in predictions.items()
            }
            assert len(predictions) == len(clusters), "Predictions not equal to clusters!"

        # Expect video file with the same name as directory (+ extension)
        assert movie_id in movie_path_map, f"Movie file not found for: {movie_id}"
        movie_path = movie_path_map[movie_id]

        data = {
            "id": movie_id,
            "path": dir,
            "movie_path": movie_path,
            "clusters": clusters,
            "n_clusters": len(clusters),
            "predictions": predictions,
        }
        dir_data[movie_id] = data

    return dir_data

movie_df, actors_df, actor_images_df = read_metadata(METADATA_DIR)
valid_actor_ids = set(actors_df.index.get_level_values("id"))
dir_data = read_datadirs(DATA_DIRS)

# Filter movies to those that have data
movie_df = movie_df.loc[dir_data.keys()]
movie_df["year"] = movie_df.year.astype(int)
movie_df["n_clusters"] = movie_df.index.map(lambda movie_id: dir_data[movie_id]["n_clusters"])

@app.get("/api/movies")
def list_movies():
    # Get annotation counts from DB
    movie_counts = db_client.get_annotation_counts()
    return [{
        "id": movie.id,
        "name": movie.name,
        "year": movie.year,
        "n_clusters": movie.n_clusters,
        "n_labeled_clusters": movie_counts[movie.id],
    } for movie in movie_df.itertuples()]

@app.get("/api/actors/{movie_id}")
def list_actors(movie_id: int):
    df = actors_df.loc[movie_id]
    actors = []
    for actor in df.itertuples():
        image_names = []
        if actor.id in actor_images_df.index:
            sub_df = actor_images_df.loc[[actor.id]]
            same_movie = (sub_df.movie_id == movie_id)
            # Add images from the correct movie first.
            image_names += sub_df[same_movie].filename.tolist()
            image_names += sub_df[~same_movie].filename.tolist()
        actors.append({
            "id": actor.id,
            "name": actor.name,
            "images": [f"images/actors/{name}" for name in image_names],
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

    # Resize frames to that we can send them faster
    MAX_SIZE = 512
    max_frame_dim = max(frame.shape[:2])
    if max_frame_dim > MAX_SIZE:
        scale = MAX_SIZE / max_frame_dim
        width, height = int(scale * frame.shape[1]), int(scale * frame.shape[0])
        dim = (width, height)
        frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

    # Encode into jpeg in-memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
    result, encimg = cv2.imencode(".jpg", frame, encode_param)

    return StreamingResponse(io.BytesIO(encimg.tobytes()), media_type="image/jpeg")

@app.get("/images/actors/{filename}")
def get_image(filename: str):
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

@app.get("/api/faces/clusters/images/{movie_id}/{cluster_id}")
def get_cluster_images(movie_id: int, cluster_id: int):
    if movie_id not in movie_df.index:
        return HTTPException(404, f"Invalid movie id {movie_id}.")

    movie_data = dir_data[movie_id]

    # Find potential labels for this cluster, in the database
    images_status = {}
    label = None
    label_time = None
    annotation = db_client.get_annotations(movie_id, cluster_id)
    if annotation is not None:
        images_status = {tag: (status == 1) for tag, status in annotation["images"]}
        label = annotation["label"]
        label_time = int(annotation["created_on"])

    # Collect static data for each image
    cluster = movie_data["clusters"][cluster_id]
    images = []
    for _, frame, box in cluster["image_data"]:
        tag = img_tag(movie_id, frame, box)
        images.append({
            "url": f"images/{tag}.jpeg",
            "full_frame_url": f"frames/{movie_id}/{frame}.jpeg",
            "approved": images_status.get(tag, True),
            "frame_index": frame,
        })

    # Expose prediction data for the API
    preds = movie_data["predictions"][cluster_id]
    predicted_actors = [actor_id for actor_id, p in preds.items() if p > PREDICTION_MIN_P]

    return {
        "cluster_id": cluster_id,
        "label": label,
        "label_time": label_time,
        "images": images,
        "n_trajectories": cluster["n_trajectories"],
        "predicted_actors": predicted_actors,
    }

@app.post("/api/faces/clusters/images/{movie_id}/{cluster_id}")
def set_cluster_labels(movie_id: int, cluster_id: int, data: ClusterLabels):
    # from images/{tag}.jpeg -> tag
    image_data = [(d.url[7:-5], int(d.approved)) for d in data.images]
    db_client.insert_annotations(movie_id, cluster_id, data.label, image_data)
    return {"status": "ok"}

@app.get("/api/faces/clusters/labels/{cluster_id}")
def get_cluster_labels(cluster_id: int):
    return {
        "cluster_id": cluster_id,
        "classes": [{"name": name, "id": i, "p": 0.54} for i, name in enumerate(SOME_NAMES)]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
