DROP TABLE IF EXISTS fact_trip CASCADE;
DROP TABLE IF EXISTS dim_datetime CASCADE;
DROP TABLE IF EXISTS dim_vendor CASCADE;
DROP TABLE IF EXISTS dim_zone CASCADE;
DROP TABLE IF EXISTS dim_ratecode CASCADE;
DROP TABLE IF EXISTS dim_payment_type CASCADE;


CREATE TABLE dim_datetime (
    datetime_id SERIAL PRIMARY KEY,
    full_timestamp TIMESTAMP NOT NULL UNIQUE,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    hour INT NOT NULL,
    day_of_week INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);


CREATE TABLE dim_zone (
    zone_id INT PRIMARY KEY,
    borough VARCHAR(50),
    zone_name VARCHAR(100)
);


CREATE TABLE dim_vendor (
    vendor_id INT PRIMARY KEY,
    vendor_name VARCHAR(100) NOT NULL
);


CREATE TABLE dim_ratecode (
    ratecode_id INT PRIMARY KEY,
    ratecode_label VARCHAR(50) NOT NULL
);


CREATE TABLE dim_payment_type (
    payment_type_id INT PRIMARY KEY,
    payment_label VARCHAR(50) NOT NULL
);


CREATE TABLE fact_trip (
    trip_id BIGSERIAL PRIMARY KEY,

    pickup_datetime_id INT NOT NULL,
    dropoff_datetime_id INT NOT NULL,

    pickup_zone_id INT,
    dropoff_zone_id INT,

    vendor_id INT,
    ratecode_id INT,
    payment_type_id INT,

    passenger_count INT,
    trip_distance DOUBLE PRECISION,

    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,

    CONSTRAINT fk_pickup_time FOREIGN KEY (pickup_datetime_id) REFERENCES dim_datetime(datetime_id),
    CONSTRAINT fk_dropoff_time FOREIGN KEY (dropoff_datetime_id) REFERENCES dim_datetime(datetime_id),

    CONSTRAINT fk_pickup_zone FOREIGN KEY (pickup_zone_id) REFERENCES dim_zone(zone_id),
    CONSTRAINT fk_dropoff_zone FOREIGN KEY (dropoff_zone_id) REFERENCES dim_zone(zone_id),

    CONSTRAINT fk_vendor FOREIGN KEY (vendor_id) REFERENCES dim_vendor(vendor_id),
    CONSTRAINT fk_ratecode FOREIGN KEY (ratecode_id) REFERENCES dim_ratecode(ratecode_id),
    CONSTRAINT fk_payment FOREIGN KEY (payment_type_id) REFERENCES dim_payment_type(payment_type_id)
);


CREATE INDEX idx_fact_trip_pickup_time ON fact_trip(pickup_datetime_id);
CREATE INDEX idx_fact_trip_dropoff_time ON fact_trip(dropoff_datetime_id);

CREATE INDEX idx_fact_trip_pickup_zone ON fact_trip(pickup_zone_id);
CREATE INDEX idx_fact_trip_dropoff_zone ON fact_trip(dropoff_zone_id);

CREATE INDEX idx_fact_trip_vendor ON fact_trip(vendor_id);
CREATE INDEX idx_fact_trip_payment ON fact_trip(payment_type_id);
