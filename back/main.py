from typing import List
import os
import glob
import json
import signal
import io
import base64

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
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
    host=os.environ.get("DB_HOST", "localhost"),
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

# Username to use if no name was given by http basic auth
DEFAULT_USER = "unknown"

# In a cluster, how many images to show for each trajectory (max)
ITEMS_PER_TRAJECTORY = 2

# Send predictions to frontend if probability is above this
PREDICTION_MIN_P = 0.40

# Max resolution (width or height) when sending a frame to the frontend
FRAME_MAX_RES = 512

# TODO: move these to config
DATA_DIR = os.environ["DATA_DIR"].rstrip("/")
FILMS_DIR = os.environ["FILMS_DIR"].rstrip("/")
METADATA_DIR = os.environ["METADATA_DIR"].rstrip("/")

def parse_actor_age(row):
    """Parse actor age at the year when a movie was released.
    """
    birthday_str = row["birthday"]
    movie_year = row["movie_year"]

    if type(birthday_str) != str or type(movie_year) != int:
        return None

    year = 0
    if len(birthday_str) == 10 or len(birthday_str) == 4:
        birthday_str = birthday_str[-4:]
        try:
            year = int(birthday_str)
        except:
            pass
    else:
        birthday_str == birthday_str.strip(".0")
        if len(birthday_str) == 4:
            try:
                year = int(birthday_str)
            except:
                pass

    age = movie_year - year
    if age >= 0 and age < 150:
        return age
    else:
        return None

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
    # actors_df = df.set_index(["movie_id", "id"]).drop(columns="movie_name")
    # actors_df["id"] = actors_df.index.get_level_values("id")
    actors_df = df.drop(columns=["movie_name", "birthplace"])

    # In some movies, the same actor has multiple roles (rare, but possible)
    # Put those cases into the same row in the actor_df
    duplicated = actors_df.duplicated(subset=["movie_id", "id"])
    for row in actors_df[duplicated].itertuples():
        selected_rows = (actors_df.movie_id == row.movie_id) & (actors_df.id == row.id)
        sub_df = actors_df[selected_rows]
        combined_role = ", ".join(filter(lambda r: r, set(sub_df.role.tolist())))
        actors_df.loc[sub_df.index, "role"] = combined_role
    actors_df = actors_df[~duplicated]

    # Finalize actors dataframe and set index [movie_id, actor_id]
    actors_df["age"] = actors_df.apply(parse_actor_age, axis=1)
    actors_df = actors_df.drop(columns=["birthday", "movie_year"])
    actors_df = actors_df.set_index(["movie_id", "id"])
    actors_df["id"] = actors_df.index.get_level_values("id")

    # actor_images.csv links images to actors (and movies)
    # Columns: index,actor_id,movie_id,filename
    actor_images_path = os.path.join(metadata_dir, "actor_images.csv")
    actor_images_df = pd.read_csv(actor_images_path, index_col="actor_id")
    actor_images_df = actor_images_df[actor_images_df.n_detections > 0].sort_index()

    # Read aspect ratios for movies
    aspect_ratios_path = os.path.join(metadata_dir, "aspect_ratios.csv")
    aspects_df = pd.read_csv(aspect_ratios_path, index_col="filename").sort_index()

    return movie_df, actors_df, actor_images_df, aspects_df

def img_tag(movie_id: int, frame: int, box: List[int]):
    """Get a 'standard' image tag as used by the face recognition stack.
    """
    # Real example of full file name: 121614:3616:235_183_293_262.jpeg
    # Face file names are <tag>.jpeg
    return f"{movie_id}:{frame}" + ":{}_{}_{}_{}".format(*box)

def parse_tag(tag: str):
    """Parse 'standard' image tag and return Tuple[int, int, int, int, int]
    with frame and box coordinates x1, y1, x2, y2 in one 5-tuple
    """
    # Real example of a tag: 121614:3616:235_183_293_262
    _, frame_str, box_str = tag.split(":", 2)
    frame = int(frame_str)
    box = tuple(int(c) for c in box_str.split("_"))
    return (frame, *box)

def parse_user(request: Request):
    """Parse the username out of a HTTPBasicAuth fastapi request.
    """
    username = DEFAULT_USER

    if "authorization" in request.headers:
        # Note: format is always like - Basic aGVsbG86d29ybGQ=
        basic = request.headers["authorization"]
        base64_part = basic[6:]
        decoded = base64.b64decode(base64_part).decode("utf-8")
        username, _ = decoded.split(":", 1)

    return username

def split_evenly(items, split_n: int):
    """Select evenly distributed split-n items from a list.
    """
    n = len(items)
    if split_n >= n:
        return items
    step = n // (split_n - 1)
    return [items[min(n - 1, m)] for m in range(0, n + step - 1, step)][:split_n]

def read_datadirs(data_dir):
    # Expand potential globs
    # data_dir contains folders like 12345-data for each movie
    dirs = glob.glob(f"{data_dir}/*-data")

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
                    file_name = f"{img_tag(movie_id, frame, box)}.jpeg"
                    if file_name in images_set:
                        valid_boxes.append((frame, box))
                t["image_bbs"] = valid_boxes
                assert len(valid_actor_ids) > 0, "Valid boxes length?"

        # Read clusters corresponing to each trajectory
        with open(clusters_file, "r") as f:
            cluster_indices = json.load(f)["clusters"]
            assert len(cluster_indices) == len(trajectories), "All trajectories need a cluster!"

        # Compute better image lookup table for clusters
        # Note: trajectories are implicitly indexed by their order in the list
        # Cluster indices are assumed to be dense, from zero
        clusters = {}
        trajectory_map = {}
        for ti, ci in enumerate(cluster_indices):
            if ci not in clusters:
                clusters[ci] = {
                    "image_data": [],
                    "n_trajectories": 0,
                    "n_shown_images": 0,  # N images that will be send to the frontend
                    "n_total_images": 0,  # Total images in related trajectories
                }
            trajectory = trajectories[ti]
            assert trajectory["index"] == ti, "Trajectory implicit index wrong?"
            # TODO: smarter selection of images to show?
            image_bbs = split_evenly(trajectory["image_bbs"], ITEMS_PER_TRAJECTORY)
            # Tuples in the list are: (trajectory_id, frame_index, bounding_box)
            clusters[ci]["image_data"] += [(ti, *ib) for ib in image_bbs]
            clusters[ci]["n_shown_images"] = len(clusters[ci]["image_data"])
            clusters[ci]["n_total_images"] += len(trajectory["image_bbs"])
            clusters[ci]["n_trajectories"] += 1

            # Uniquely map (frame, *box) -> trajectory id for every shown image
            trajectory_map.update({tuple([frame, *box]): ti for frame, box in image_bbs})

        # Read per-cluster predictions
        with open(predictions_file, "r") as f:
            predictions = json.load(f)["predictions"]
            # Convert keys to integers (JSON only has string keys)
            predictions = {
                int(cluster_id): {int(actor_id): p for actor_id, p in cluster_preds.items()}
                for cluster_id, cluster_preds in predictions.items()
            }
            assert len(predictions) == len(clusters), "Predictions not equal to clusters!"

        if movie_id in movie_path_map:
            movie_path = movie_path_map[movie_id]
            # Read movie fps from file so that frontend can compute hh:mm:ss for frames!
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            # Read display aspect ratio-adjusted frame resolution
            basename = os.path.basename(movie_path)
            width = int(aspects_df.at[basename, "display_width"])
            height = int(aspects_df.at[basename, "display_height"])
            resolution = (width, height)
            # Compute a scaling factor, that is used to scale frames down when sending
            # to the frontend
            scaling_factor = min(1.0, FRAME_MAX_RES / max(width, height))
            cap.release()
        else:
            fps = 25.0
            scaling_factor = 1.0
            resolution = (0, 0)
            movie_path = None
            print(f"Movie file not found for: {movie_id}")

        data = {
            "id": movie_id,
            "path": dir,
            "movie_path": movie_path,
            "clusters": clusters,
            "n_clusters": len(clusters),
            "predictions": predictions,
            "trajectory_map": trajectory_map,
            "fps": fps,
            "resolution": resolution,
            "scaling_factor": scaling_factor,
        }
        dir_data[movie_id] = data

    return dir_data

movie_df, actors_df, actor_images_df, aspects_df = read_metadata(METADATA_DIR)
valid_actor_ids = set(actors_df.index.get_level_values("id"))
dir_data = read_datadirs(DATA_DIR)

# Filter movies to those that have data
movie_df = movie_df.loc[dir_data.keys()]
movie_df["year"] = movie_df.year.astype(int)
movie_df["n_clusters"] = movie_df.index.map(lambda movie_id: dir_data[movie_id]["n_clusters"])
movie_df["fps"] = movie_df.index.map(lambda movie_id: dir_data[movie_id]["fps"])

def get_movie_data(movie_ids: List[int], movie_counts):
    """Utility method to get movie data in a JSON-digestible format.
    """
    if not all(id in movie_df.index for id in movie_ids):
        return None

    return [{
        "id": int(movie_df.at[id, "id"]),
        "name": movie_df.at[id, "name"],
        "year": int(movie_df.at[id, "year"]),
        "n_clusters": int(movie_df.at[id, "n_clusters"]),
        "n_labeled_clusters": movie_counts[id],
        "fps": movie_df.at[id, "fps"],
    } for id in movie_ids]

@app.get("/api/movies/{movie_id}")
def get_movie(movie_id: int, response: Response):
    """Get metadata about a single movie.
    """
    movie_counts = db_client.get_annotation_counts(movie_id)
    if movie_counts is None:
        response.status_code = 500
        return {
            "error": "Could not read movie label counts from database.",
            "code": "LABEL_COUNT_READ",
        }

    movie_data = get_movie_data([movie_id], movie_counts)

    if movie_data is None:
        raise HTTPException(404, error=f"No such movie {movie_id}.")

    return movie_data[0]

@app.get("/api/movies")
def list_movies(response: Response):
    """Get metadata about all movies available in the backend.
    """
    movie_counts = db_client.get_annotation_counts()
    if movie_counts is None:
        response.status_code = 500
        return {
            "error": "Could not read movie label counts from database.",
            "code": "LABEL_COUNT_READ",
        }

    all_movie_ids = movie_df.id.tolist()
    movie_data = get_movie_data(all_movie_ids, movie_counts)

    return movie_data

@app.get("/api/actors/{movie_id}")
def list_actors(movie_id: int):
    # Get the number of current images labeled, global and movie level
    global_count, movie_count = db_client.get_actor_counts(movie_id)

    df = actors_df.loc[movie_id]
    actors = []
    for actor in df.itertuples():
        image_names = []
        if actor.id in actor_images_df.index:
            sub_df = actor_images_df.loc[[actor.id]].sort_values("n_detections")
            same_movie = (sub_df.movie_id == movie_id)
            # Add images from the correct movie first.
            image_names += sub_df[same_movie].filename.tolist()
            image_names += sub_df[~same_movie].filename.tolist()
        actors.append({
            "id": actor.id,
            "name": actor.name,
            "role": actor.role,
            "age": None if pd.isna(actor.age) else int(actor.age),
            "images": [f"images/actors/{name}" for name in image_names],
            "movie_count": movie_count[actor.id],
            "global_count": global_count[actor.id],
        })
    return actors

@app.get("/images/frames/{movie_id}/{frame_index}_{box}.jpeg")
def get_frame(movie_id: int, frame_index: int, box: str):
    if not movie_id in dir_data:
        raise HTTPException(404, error=f"No such movie {movie_id}.")

    if dir_data[movie_id]["movie_path"] is None:
        # This happens if the FILMS_DIR environment variable was improperly set,
        # or if no movie file (eg. mp4, etc.) was found in FILMS_DIR for this film.
        raise HTTPException(500, error=f"No frame data for film.")

    cap = cv2.VideoCapture(dir_data[movie_id]["movie_path"])

    if not cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index):
        raise HTTPException(400, error="Bad request!")

    box_split = box.split("-")
    try:
        box_split = [int(c) for c in box_split]
    except:
        raise HTTPException(400, error="Bad request!")

    if len(box_split) != 4:
        raise HTTPException(400, error="Bad request!")

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise HTTPException(500, error="Error reading movie.")

    w, h = dir_data[movie_id]["resolution"]
    scale = dir_data[movie_id]["scaling_factor"]
    scaled_w = round(scale * w)
    scaled_h = round(scale * h)
    box = [round(c * scale) for c in box_split]

    # Scale frame if needed to correct size
    frame = cv2.resize(frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)

    # Draw bounding box on frame to highlight actor (color is BGR)
    color = (255, 255, 255)
    thickness = 1
    frame = cv2.rectangle(frame, tuple(box[:2]), tuple(box[2:]), color, thickness)

    # Encode into jpeg in-memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
    result, encimg = cv2.imencode(".jpg", frame, encode_param)

    return StreamingResponse(io.BytesIO(encimg.tobytes()), media_type="image/jpeg")

@app.get("/images/actors/{filename}")
def get_image(filename: str):
    # Filename can't contain directory separators
    for sep in os.sep:
        filename = filename.replace(sep, "")

    file_path = os.path.join(METADATA_DIR, "actor_images", filename)

    if not os.path.exists(file_path):
        raise HTTPException(404, error=f"File not found.")

    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )

@app.get("/images/{movie_id}:{frame}:{bbox_str}.jpeg")
def get_image(movie_id: int, frame: int, bbox_str: str):
    if movie_id not in movie_df.index:
        raise HTTPException(404, error=f"Invalid movie id {movie_id}.")

    bbox = [int(c) for c in bbox_str.replace("/", "").split("_")]
    tag = img_tag(movie_id, frame, bbox)

    movie_dir = dir_data[movie_id]["path"]
    file_path = os.path.join(movie_dir, "images", f"{tag}.jpeg")

    if not os.path.exists(file_path):
        raise HTTPException(404, error=f"File not found.")

    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )

@app.get("/api/faces/clusters/{movie_id}/{cluster_id}")
def get_cluster_data(movie_id: int, cluster_id: int, request: Request, response: Response):
    """Main endpoint to get all data of a cluster.
    """
    if movie_id not in movie_df.index:
        raise HTTPException(404, error=f"Invalid movie id {movie_id}.")

    movie_data = dir_data[movie_id]
    data_cluster_id = cluster_id

    # Default statuses for clusters and images if the database didn't have records
    DEFAULT_IMAGE_STATUS = "same"
    DEFAULT_CLUSTER_STATUS = "labeled"

    username = parse_user(request)
    annotation = db_client.get_annotations(username, movie_id, data_cluster_id)

    if annotation is None:
        # Rare database error occurred, show in response code
        response.status_code = 500
        return {
            "error": "Couldn't read cluster info from database.",
            "code": "DATABASE_READ_ERROR",
        }

    images_statuses = {tag: status for tag, status in annotation.get("images", [])}
    username = annotation.get("username", None)
    label = annotation.get("label", None)
    label_time = annotation.get("created_on", None)
    status = annotation.get("status", DEFAULT_CLUSTER_STATUS)

    # Collect static data for each image
    cluster = movie_data["clusters"][data_cluster_id]
    images = []
    for _, frame, box in cluster["image_data"]:
        tag = img_tag(movie_id, frame, box)
        box_joined_str = "-".join(map(str, box))
        images.append({
            "url": f"images/{tag}.jpeg",
            "full_frame_url": f"images/frames/{movie_id}/{frame}_{box_joined_str}.jpeg",
            "status": images_statuses.get(tag, DEFAULT_IMAGE_STATUS),
            "frame_index": frame,
        })

    # Expose prediction data for the API
    preds = movie_data["predictions"][data_cluster_id]
    predicted_actors = [actor_id for actor_id, p in preds.items() if p > PREDICTION_MIN_P]

    return {
        "username": username,
        "cluster_id": cluster_id,
        "label": label,
        "label_time": label_time,
        "status": status,
        "images": images,
        "n_trajectories": cluster["n_trajectories"],
        "predicted_actors": predicted_actors,
    }

@app.post("/api/faces/clusters/{movie_id}/{cluster_id}")
def set_cluster_data(
    movie_id: int, cluster_id: int, data: ClusterLabels, request: Request, response: Response
):
    """Main endpoint to save cluster data to persistent storage. Eg. assign label.
    """
    if movie_id not in dir_data:
        raise HTTPException(404, error=f"Invalid movie id {movie_id}.")

    movie_data = dir_data[movie_id]
    data_cluster_id = cluster_id

    image_data_db = []
    for image in data.images:
        # from images/{tag}.jpeg -> tag
        tag = image.url[7:-5]
        frame_and_box = parse_tag(tag)
        trajectory_id = movie_data["trajectory_map"][frame_and_box]
        image_data_db.append((tag, image.status, trajectory_id))

    username = parse_user(request)
    success = db_client.insert_annotations(
        username, movie_id, data_cluster_id, data.label, image_data_db, data.status, data.time
    )

    if success:
        return {"status": "ok"}
    else:
        # Rare database error occurred, produce error response.
        response.status_code = 500
        return {
            "error": "Couldn't save cluster info to database.",
            "code": "DATABASE_WRITE_ERROR",
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
