CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120),
    email VARCHAR(160)
);

CREATE TABLE organizations (
    org_id INT AUTO_INCREMENT PRIMARY KEY,
    org_name VARCHAR(120)
);

-- add all other tables here
