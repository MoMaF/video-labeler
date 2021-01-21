import pandas as pd
import psycopg2
import psycopg2.extras
import pandas.io.sql as sqlio

# Change this if using a remote database.
host="localhost"
port=5432
user="admin"
database="db"
password="test"

conn = psycopg2.connect(
    user=user,
    password=password,
    host=host,
    port=port,
    database=database,
)
query = """SELECT *
    FROM (
        SELECT id,username,movie_id,cluster_id,status as cluster_status,label,n_images,EXTRACT(EPOCH FROM created_on) as created_on,processing_time FROM clusters
        WHERE status <> 'labeled' OR label IS NOT NULL
    ) AS clusters
    INNER JOIN (
        SELECT cluster_id as id_ref,tag,status as image_status,trajectory FROM images
    ) AS images
    ON (clusters.id = images.id_ref);"""

df = sqlio.read_sql_query(query, conn)
df.to_csv("labels.csv", index_label="index")
conn.close()
