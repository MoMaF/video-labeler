CREATE TYPE cluster_status AS ENUM ('labeled', 'discarded', 'postponed', 'mixed');

-- same = image shows majority actor of cluster
-- different = image is faulty or shows a different actor
-- invalid = image is not a face
CREATE TYPE image_status AS ENUM ('same', 'different', 'invalid');

CREATE TABLE clusters (
	"id" serial			PRIMARY KEY,
	"username"			VARCHAR(64) NOT NULL,
	"movie_id"			INTEGER NOT NULL,
	"cluster_id"		INTEGER NOT NULL,
	"status"			cluster_status NOT NULL,
	"label"				VARCHAR(64),
	"n_images"			INTEGER NOT NULL,
	"created_on"		TIMESTAMP NOT NULL DEFAULT NOW(),
	"processing_time"	INTEGER NOT NULL
);

CREATE TABLE images (
	"cluster_id"	INTEGER REFERENCES clusters(id),
	"tag"			VARCHAR(64) NOT NULL,
	"status"		image_status NOT NULL,
	"trajectory"	INTEGER NOT NULL
);
