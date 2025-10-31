INSERT INTO users (full_name, email) VALUES
('Alex Chen',  'alex@citymail.cuny.edu'),
('James Wilson','james@citymail.cuny.edu');

-- One organization
INSERT INTO organizations (org_name) VALUES
('Zahn Innovation');

-- One event under that organization
INSERT INTO events (org_id, title, venue, starts_at, ends_at, capacity, is_published)
SELECT o.org_id, 'Data Hackathon Night', 'Shepard Hall',
       NOW() + INTERVAL 7 DAY,
       NOW() + INTERVAL 7 DAY + INTERVAL 2 HOUR,
       200, TRUE
FROM organizations o
WHERE o.org_name = 'Zahn Innovation';

-- One ticket type for that event
INSERT INTO tickets (event_id, name, price_cents, qty_total)
SELECT e.event_id, 'General Admission', 1500, 150
FROM events e
WHERE e.title = 'Data Hackathon Night';