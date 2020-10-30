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

    def insert_annotations(self, movie_id, cluster_id, label, images):
        """Batch insert annotations of images, into database.
        """
        cursor = self.conn.cursor()

        # Check if cluster exists already
        q1 = "SELECT id FROM clusters WHERE movie_id = %s AND cluster_id = %s;"
        cursor.execute(q1, (movie_id, cluster_id))
        result = cursor.fetchone()

        # Delete the old records if they existed
        existed = result is not None
        if existed:
            db_cluster_id = result[0]
            cursor.execute("DELETE FROM images WHERE cluster_id = %s;", (db_cluster_id,))
            cursor.execute("DELETE FROM clusters WHERE id = %s;", (db_cluster_id,))

        # Create cluster (or recreate...)
        q2 = """INSERT INTO
            clusters (movie_id, cluster_id, label, n_images)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        cursor.execute(q2, (movie_id, cluster_id, label, len(images)))
        db_cluster_id = cursor.fetchone()[0]

        # Add images that were in the cluster. Image list - tuples (tag: str, status: int)
        q3 = "INSERT INTO images (cluster_id, tag, status) VALUES %s;"
        psycopg2.extras.execute_values(
            cursor, q3, [(db_cluster_id, tag, status) for tag, status in images],
            template=None, page_size=100,
        )

        self.conn.commit()
        cursor.close()

    def get_annotations(self, movie_id, cluster_id):
        cursor = self.conn.cursor()
        q1 = """SELECT id, label, n_images, created_on
            FROM clusters
            WHERE movie_id = %s AND cluster_id = %s;
        """
        cursor.execute(q1, (movie_id, cluster_id))
        result = cursor.fetchone()

        if result is None:
            return None

        db_cluster_id, label, n_images, created_on = result

        q2 = "SELECT tag, status FROM images WHERE cluster_id = %s;"
        cursor.execute(q2, (db_cluster_id,))
        images = cursor.fetchall()

        return {
            "movie_id": movie_id,
            "cluster_id": cluster_id,
            "label": label,
            "created_on": created_on,
            "images": images,  # tuples (image_tag: str, status: int)
        }


if __name__ == "__main__":
    client = DatabaseClient(password="test")
    client.insert_annotations(
        12345, 0, 100, [("image_1", 1), ("image_2", 0), ("image_3", 1), ("image_4", 0)]
    )

    #data = client.get_annotations(12345, 0)
    #pass
