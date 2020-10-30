CREATE TABLE clusters (
	"id" serial		PRIMARY KEY,
	"movie_id"		INTEGER NOT NULL,
    "cluster_id"	INTEGER NOT NULL,
    "label"			INTEGER,
	"n_images"		INTEGER NOT NULL,
	"created_on"	TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE images (
	"cluster_id"	INTEGER REFERENCES clusters(id),
    "tag"			VARCHAR(64) NOT NULL,
	"status"		INTEGER NOT NULL DEFAULT 0
);
