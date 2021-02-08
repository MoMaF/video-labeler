from datetime import datetime
from collections import defaultdict
from typing import Optional
import traceback

import psycopg2
import psycopg2.extras
import psycopg2.errors
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
        self.conn.autocommit = False

    def close(self):
        if self.conn:
            self.conn.close()

    def insert_annotations(self, username, movie_id, cluster_id, label, images, status, time):
        """Batch insert annotations of images, into database.

        Args:
            username (str): user name
            movie_id (int): movie id
            cluster_id (int): movie-specific cluster index
            label (str): cluster label (actor id string, or object, etc.)
            images (List): tuples of images + status + t_id
                Example: [("image_tag", "same", trajectory_id int), ...]
            status (str): cluster status: 'labeled', 'discarded', 'postponed', 'mixed'
            time (int): processing time the user took to label this cluster, milliseconds
        """
        insert_success = True
        cursor = self.conn.cursor()

        # Determine if the cluster is in initial state (=everything empty/unchanged)
        # If yes, nothing will be inserted, but only removed to save db space/performance
        is_default = True
        is_default = is_default and label is None
        is_default = is_default and status == "labeled"
        is_default = is_default and all(img[1] == "same" for img in images)

        try:
            # Check if cluster exists already
            q1 = """SELECT id, processing_time
                FROM clusters
                WHERE username = %s AND movie_id = %s AND cluster_id = %s;
                """
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

            if not is_default:
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
        except psycopg2.Error as e:
            insert_success = False
            self.conn.rollback()
            traceback.print_exc()
        finally:
            cursor.close()
            return insert_success

    def get_annotations(self, username, movie_id, cluster_id):
        cursor = self.conn.cursor()
        q1 = """SELECT id, username, label, status, n_images, EXTRACT(EPOCH FROM created_on)
            FROM clusters
            WHERE movie_id = %s AND cluster_id = %s;
        """

        try:
            cursor.execute(q1, (movie_id, cluster_id))
        except psycopg2.errors.InFailedSqlTransaction as err:
            traceback.print_exc()
            return None

        results = cursor.fetchall()
        if not results:
            return {}

        # Find result by current user, if it existed
        first_result = results[0]
        for result in results[1:]:
            if result[1] == username:
                first_result = result
                break

        db_cluster_id, cluster_user, label, cluster_status, n_images, created_on = first_result

        q2 = "SELECT tag, status FROM images WHERE cluster_id = %s;"
        try:
            cursor.execute(q2, (db_cluster_id,))
        except psycopg2.errors.InFailedSqlTransaction as err:
            traceback.print_exc()
            return None

        images = cursor.fetchall()
        # Psycopg opens transactions even with SELECT queries, so we close it here:
        self.conn.commit()
        cursor.close()

        return {
            "movie_id": movie_id,
            "cluster_id": cluster_id,
            "username": cluster_user,
            "label": label,
            "status": cluster_status,
            "created_on": int(created_on),
            "images": images,  # tuples (image_tag: str, status: str)
        }

    def get_annotation_counts(self, movie_id: Optional[int] = None):
        """Return count of how many clusters have been labeled, per movie.
        """
        movie_clause = ""
        if movie_id is not None:
            movie_clause = f"AND movie_id = {movie_id}"

        q = f"""SELECT movie_id, COUNT(DISTINCT cluster_id)
            FROM clusters
            WHERE label IS NOT NULL {movie_clause}
            GROUP BY movie_id;
        """

        movie_counts = None
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(q)
                result = cursor.fetchall()
                # Psycopg opens transactions even with SELECT queries, so we close it here:
                self.conn.commit()
                counts = {movie_id: count for movie_id, count in result}
                movie_counts = defaultdict(lambda: 0, counts)
            except psycopg2.errors.InFailedSqlTransaction as err:
                traceback.print_exc()

        return movie_counts

    def get_actor_counts(self, movie_id: int):
        """Get labeled images count on movie level and global level, for each
        every actor in the database.
        """
        def get_counts(movie_id: Optional[int] = None):
            """Utility function.
            """
            movie_clause = ""
            if movie_id is not None:
                movie_clause = f"AND movie_id = {movie_id}"

            # Query to get actor level image counts
            # Counts images labeled in the tool (usually 2x trajectories in a cluster)
            q = f"""SELECT label, COUNT(trajectory)
                FROM (
                    SELECT id, movie_id, label FROM clusters
                    WHERE status = 'labeled' AND label IS NOT NULL {movie_clause}
                ) AS clusters
                INNER JOIN (
                    SELECT * FROM images
                    WHERE status = 'same'
                ) AS images
                ON (clusters.id = images.cluster_id)
                GROUP BY label;"""

            actor_counts = None
            with self.conn.cursor() as cursor:
                try:
                    cursor.execute(q)
                    result = cursor.fetchall()
                    # Psycopg opens transactions even with SELECT queries, so we close it here:
                    self.conn.commit()
                    counts = {actor_id: count for actor_id, count in result}
                    actor_counts = defaultdict(lambda: 0, counts)
                except psycopg2.errors.InFailedSqlTransaction as err:
                    traceback.print_exc()

            return actor_counts

        count_global = get_counts()
        count_movie = get_counts(movie_id)

        return count_global, count_movie
