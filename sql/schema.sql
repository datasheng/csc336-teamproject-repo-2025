CREATE TABLE IF NOT EXISTS users(
  user_id   BIGSERIAL PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email     VARCHAR(160) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS organizations(
  org_id   BIGSERIAL PRIMARY KEY,
  org_name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS org_members(
  org_id  BIGINT NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(user_id)        ON DELETE CASCADE,
  role    VARCHAR(20) NOT NULL CHECK (role IN ('owner','admin','member')),
  PRIMARY KEY (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id BIGSERIAL PRIMARY KEY,
    org_id BIGINT NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    event_name VARCHAR(150) NOT NULL,
    event_date DATE NOT NULL,
    location VARCHAR(200),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

