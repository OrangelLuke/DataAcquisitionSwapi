-- type in command line "sqlite3 StarWars.db" to create a new database named "StarWars.db" 

CREATE TABLE IF NOT EXISTS people (
    name TEXT,
    height INTEGER ,
    mass INTEGER ,
    hair_color TEXT,
    skin_color TEXT,
    eye_color TEXT,
    birth_year ,
    gender TEXT,
    created TEXT,
    edited TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;


.mode csv people;
.import people.csv people


CREATE TABLE IF NOT EXISTS planets (
	name TEXT,
    rotation_period INTEGER,
    orbital_period INTEGER,
    diameter INTEGER,
    climate TEXT,
    gravity TEXT,
    terrain TEXT,
    surface_water INTEGER,
    population INTEGER,
    created TEXT,
    edited TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

.mode csv planets;
.import planets.csv planets


CREATE TABLE IF NOT EXISTS vehicles (
	name TEXT,
    model TEXT,
    manufacturer TEXT,
    cost_in_credits INTEGER,
    length INTEGER,
    max_atmosphering_speed INTEGER,
    crew INTEGER,
    passengers INTEGER,
    cargo_capacity INTEGER,
    consumables TEXT,
    vehicle_class TEXT,
    created  TEXT,
    edited  TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

.mode csv vehicles;
.import vehicles.csv vehicles   

CREATE TABLE IF NOT EXISTS species (
	name  TEXT,
    classification  TEXT,
    designation  TEXT,
    average_height INTEGER,
    skin_colors  TEXT,
    hair_colors  TEXT,
    eye_colors  TEXT,
    average_lifespan INTEGER,
    language TEXT,
    created TEXT,
    edited TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

.mode csv species;
.import species.csv species

CREATE TABLE IF NOT EXISTS films (
	title TEXT,
    episode_id INTEGER,
    opening_crawl TEXT,
    director TEXT,
    producer TEXT,
    release_date TEXT,
    created TEXT,
    edited TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

.mode csv films;
.import films.csv films


CREATE TABLE IF NOT EXISTS starships (
	name TEXT,
    model TEXT,
    manufacturer TEXT,
    cost_in_credits INTEGER,
    length INTEGER,
    max_atmosphering_speed INTEGER,
    crew INTEGER,
    passengers INTEGER,
    cargo_capacity INTEGER,
    consumables TEXT,
    hyperdrive_rating INTEGER,
    MGLT INTEGER,
    starship_class TEXT,
    created TEXT,
    edited TEXT,
    id TEXT PRIMARY KEY
) WITHOUT ROWID;

.mode csv starships;
.import starships.csv starships

CREATE TABLE IF NOT EXISTS people_films_interaction (
	people TEXT,
    films TEXT,
    PRIMARY KEY (people, films),
    FOREIGN KEY(people) REFERENCES people(id)
    FOREIGN KEY(films) REFERENCES films(id)
) WITHOUT ROWID;

.mode csv people_films_interaction;
.import people_films_interaction.csv people_films_interaction

CREATE TABLE IF NOT EXISTS people_planets_interaction (
	people TEXT,
    planets TEXT,
    PRIMARY KEY (people, planets),
    FOREIGN KEY(people) REFERENCES people(id)
    FOREIGN KEY(planets) REFERENCES planets(id)
) WITHOUT ROWID;

.mode csv people_planets_interaction;
.import people_planets_interaction.csv people_planets_interaction

CREATE TABLE IF NOT EXISTS people_species_interaction (
	people TEXT,
    species TEXT,
    PRIMARY KEY (people, species),
    FOREIGN KEY(people) REFERENCES people(id)
    FOREIGN KEY(species) REFERENCES species(id)
) WITHOUT ROWID;

.mode csv people_species_interaction;
.import people_species_interaction.csv people_species_interaction

CREATE TABLE IF NOT EXISTS people_starships_interaction (
	people TEXT,
    starships TEXT,
    PRIMARY KEY (people, starships),
    FOREIGN KEY(people) REFERENCES people(id)
    FOREIGN KEY(starships) REFERENCES starships(id)
) WITHOUT ROWID;

.mode csv people_starships_interaction;
.import people_starships_interaction.csv people_starships_interaction

CREATE TABLE IF NOT EXISTS people_vehicles_interaction (
	people TEXT,
    vehicles TEXT,
    PRIMARY KEY (people, vehicles),
    FOREIGN KEY(people) REFERENCES people(id)
    FOREIGN KEY(vehicles) REFERENCES vehicles(id)
) WITHOUT ROWID;

.mode csv people_vehicles_interaction;
.import people_vehicles_interaction.csv people_vehicles_interaction

CREATE TABLE IF NOT EXISTS planets_films_interaction (
	planets TEXT,
    films TEXT,
    PRIMARY KEY (planets, films),
    FOREIGN KEY(planets) REFERENCES planets(id)
    FOREIGN KEY(films) REFERENCES films(id)
) WITHOUT ROWID;

.mode csv planets_films_interaction;
.import planets_films_interaction.csv planets_films_interaction

CREATE TABLE IF NOT EXISTS vehicles_films_interaction (
	vehicles TEXT,
    films TEXT,
    PRIMARY KEY (vehicles, films),
    FOREIGN KEY(vehicles) REFERENCES vehicles(id)
    FOREIGN KEY(films) REFERENCES films(id)
) WITHOUT ROWID;

.mode csv vehicles_films_interaction;
.import vehicles_films_interaction.csv vehicles_films_interaction

CREATE TABLE IF NOT EXISTS species_planets_interaction (
	species TEXT,
    planets TEXT,
    PRIMARY KEY (species, planets),
    FOREIGN KEY(species) REFERENCES species(id)
    FOREIGN KEY(planets) REFERENCES planets(id)
) WITHOUT ROWID;

.mode csv species_planets_interaction;
.import species_planets_interaction.csv species_planets_interaction

CREATE TABLE IF NOT EXISTS species_films_interaction (
	species TEXT,
    films TEXT,
    PRIMARY KEY (species, films),
    FOREIGN KEY(species) REFERENCES species(id)
    FOREIGN KEY(films) REFERENCES films(id)
) WITHOUT ROWID;

.mode csv species_films_interaction;
.import species_films_interaction.csv species_films_interaction

CREATE TABLE IF NOT EXISTS films_starships_interaction (
	starships TEXT,
    films TEXT,
    PRIMARY KEY (starships, films),
    FOREIGN KEY(starships) REFERENCES starships(id)
    FOREIGN KEY(films) REFERENCES films(id)
) WITHOUT ROWID;

.mode csv films_starships_interaction;
.import films_starships_interaction.csv films_starships_interaction
