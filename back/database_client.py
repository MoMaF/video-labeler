from datetime import datetime
from collections import defaultdict

import psycopg2
import psycopg2.extras
import pandas as pd

class DatabaseClient:
    def __init__(
        self, host="localhost", port=5432, user="admin", database="db", password=""
    ):
        self.conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
        )

    def close(self):
        print("Closing")
        if self.conn:
            self.conn.close()

    def insert_annotations(self, username, movie_id, cluster_id, label, images, status, time):
        """Batch insert annotations of images, into database.

        Args:
            username (str): user name
            movie_id (int): movie id
            cluster_id (int): movie-specific cluster index
            label (int): cluster label (equals actor id)
            images (List): tuples of images + status + t_id
                Example: [("image_tag", "same", trajectory_id int), ...]
            status (str): cluster status: 'labeled', 'discarded', 'postponed', 'mixed'
            time (int): processing time the user took to label this cluster, milliseconds
        """
        cursor = self.conn.cursor()

        # Check if cluster exists already
        q1 = "SELECT id, processing_time FROM clusters WHERE username = %s AND movie_id = %s AND cluster_id = %s;"
        cursor.execute(q1, (username, movie_id, cluster_id))
        result = cursor.fetchone()

        # Delete the old records if they existed
        existed = result is not None
        if existed:
            db_cluster_id, time_so_far = result
            cursor.execute("DELETE FROM images WHERE cluster_id = %s;", (db_cluster_id,))
            cursor.execute("DELETE FROM clusters WHERE id = %s;", (db_cluster_id,))

            # Add up so that processing time is the total time for this user
            time += time_so_far

        # Create cluster (or recreate...)
        q2 = """INSERT INTO
            clusters (username, movie_id, cluster_id, status, label, n_images, processing_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cursor.execute(q2, (username, movie_id, cluster_id, status, label, len(images), time))
        db_cluster_id = cursor.fetchone()[0]

        # Add images that were in the cluster.
        # Image list - tuples (tag: str, status: str, trajectory: int)
        q3 = "INSERT INTO images (cluster_id, tag, status, trajectory) VALUES %s;"
        psycopg2.extras.execute_values(
            cursor, q3, [(db_cluster_id, tag, status, t_id) for tag, status, t_id in images],
            template=None, page_size=100,
        )

        self.conn.commit()
        cursor.close()

    def get_annotations(self, username, movie_id, cluster_id):
        cursor = self.conn.cursor()
        q1 = """SELECT id, username, label, status, n_images, EXTRACT(EPOCH FROM created_on)
            FROM clusters
            WHERE movie_id = %s AND cluster_id = %s;
        """
        cursor.execute(q1, (movie_id, cluster_id))
        results = cursor.fetchall()

        if not results:
            return None

        # Find result by current user, if it existed
        first_result = results[0]
        for result in results[1:]:
            if result[1] == username:
                first_result = result
                break

        db_cluster_id, cluster_user, label, cluster_status, n_images, created_on = first_result

        q2 = "SELECT tag, status FROM images WHERE cluster_id = %s;"
        cursor.execute(q2, (db_cluster_id,))
        images = cursor.fetchall()

        return {
            "movie_id": movie_id,
            "cluster_id": cluster_id,
            "username": cluster_user,
            "label": label,
            "created_on": created_on,
            "images": images,  # tuples (image_tag: str, status: str)
        }

    def get_annotation_counts(self):
        """Return count of how many clusters have been labeled, per movie.
        """
        q = """SELECT movie_id, COUNT(DISTINCT cluster_id)
            FROM public.clusters
            WHERE label IS NOT NULL
            GROUP BY movie_id;
        """

        cursor = self.conn.cursor()
        cursor.execute(q)

        result = cursor.fetchall()

        movie_counts = {movie_id: count for movie_id, count in result}
        return defaultdict(int, movie_counts)
