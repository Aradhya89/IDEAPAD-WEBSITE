
    CREATE TABLE events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    title TEXT NOT NULL,
    banner TEXT NOT NULL,
    banner_public_id TEXT,
    date DATE NOT NULL,
    time TIME NOT NULL,
    description TEXT NOT NULL
);


-- user table
CREATE TABLE if not exists users (
    email VARCHAR(255) PRIMARY KEY,

    google_id VARCHAR(50) UNIQUE NOT NULL,

    full_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),

    profile_picture TEXT,

    email_verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    last_login TIMESTAMPTZ DEFAULT NOW());


-- registration table
CREATE TABLE IF NOT EXISTS registrations(

    email VARCHAR(255) PRIMARY KEY,


    full_name VARCHAR(255) NOT NULL,
    rollno VARCHAR(50) NOT NULL,
    batch VARCHAR(30) NOT NULL,
    branch VARCHAR(100) NOT NULL,

    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY(email)
    REFERENCES users(email)
    ON DELETE CASCADE

);

CREATE TABLE IF NOT EXISTS event_registrations(

    email VARCHAR(255) NOT NULL REFERENCES users(email)
    ON DELETE CASCADE,
    event_id BIGINT NOT NULL
    REFERENCES events(id) ON DELETE CASCADE,


    full_name VARCHAR(255) NOT NULL,
    rollno VARCHAR(50) NOT NULL,
    batch VARCHAR(30) NOT NULL,
    branch VARCHAR(100) NOT NULL,

    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (email,event_id)

);

