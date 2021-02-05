# video-labeler

Video labeling backend and frontend for MoMaF. The backend reads many individual data folders `12345-data` (see: [extraction pipeline](https://github.com/MoMaF/facerec/tree/develop)) and provides a frontend for annotation of faces in movies.

The backend uses FastAPI (Python). The frontend is a React-redux web application. The database uses PostgreSQL.

Recommended preinstalled software to run this locally:

- Python 3.8 or greater. For the backend.
- `npm` and `node` to run and eventually compile the frontend.
- PostgreSQL 13 for the database. The easy way here is using the [included Docker setup](./DATABASE.md).

___

## Running locally

To make it run, three different types of data is needed. The backend will read this data from environment variables `DATA_DIR`, `METADATA_DIR` and `FILMS_DIR`.

___

#### `DATA_DIR`: Extracted film data.

Data from the [extraction pipeline](https://github.com/MoMaF/facerec/tree/develop). This means, 1 or more samples of extracted film data with a directory such as `12345-data`. Put all of these folders in a parent directory of your choosing and export its path as `export DATA_DIR="/path/to/the/folder"`. A full example can be found here: [113528-data](https://drive.google.com/file/d/1DjILPXwae9GcKkzVusGcwMTGNx0DlXzm/view?usp=sharing).

#### `METADATA_DIR`: Data and images of actors.

Metadata with information about actors, and archived images of actors. Export path as `export METADATA_DIR="/path/to/the/metadata"`. Download here: [link](https://drive.google.com/file/d/1dEziNOTIZUGodcpveCHFn20K8IVflwuG/view?usp=sharing).

#### `FILMS_DIR`: Raw video files of the movies at hand.

Actual video files. These are used to show the full frames of a movie in the frontend. Not strictly needed for the backend to start. Export path as `export FILMS_DIR="/path/to/the/films"` where files have the format `12345-CoolMovieFilms.mp4`, etc.

___

#### After doing the above, run the software:

1. **Database:** setup a postgres database to run on `localhost` with a user `admin` and password `test`. The port should be the postgres default `5432`, and there should be a database named `db`. Initialize it with the schema defined at `database/create.sql`. The [easiest way to do this is using Docker](./DATABASE.md).

2. **Backend:** install python requirements (`back/requirements.txt`) and run the backend by: `python back/main.py`. This requires the environment variables `DATA_DIR`, `METADATA_DIR`, `FILMS_DIR` and `DB_PASSWORD`. Set `DB_PASSWORD=test` (your local postgres password). Run the backend by `python back/main.py`. This will run the backend at localhost:5000.

3. **Frontend:** go into the frontend (`cd front-app`) and run `npm install` to install dependencies. Run the frontend by `npm run start`. The frontend now shows in a browser at localhost:3000.

___

**Working setup**

If everything worked out, the frontend should look something like:

![Labeler front](https://gist.githubusercontent.com/ekreutz/249a6cbe4203194e66b846057f6415bf/raw/labeler_main.png)

___

# Folder `extra`

Contains independent scripts that are useful, but not needed in any way for the project to run.

- `extra/database_to_csv.py`: Example of how to retrieve a database dump (CSV) from the PostgreSQL database that is used in this project.
