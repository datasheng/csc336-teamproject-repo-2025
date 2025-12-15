INSERT INTO users (full_name, email) VALUES
('Alex Chen',  'alex@citymail.cuny.edu'),
('James Wilson','james@citymail.cuny.edu');


INSERT INTO organizations (org_name) VALUES
('Zahn Innovation');


INSERT INTO events (org_id, title, venue, starts_at, ends_at, capacity, is_published)
SELECT o.org_id, 'Data Hackathon Night', 'Shepard Hall',
       NOW() + INTERVAL 7 DAY,
       NOW() + INTERVAL 7 DAY + INTERVAL 2 HOUR,
       200, TRUE
FROM organizations o
WHERE o.org_name = 'Zahn Innovation';


INSERT INTO tickets (event_id, name, price_cents, qty_total)
SELECT e.event_id, 'General Admission', 1500, 150
FROM events e
WHERE e.title = 'Data Hackathon Night';

INSERT INTO users (full_name, email, password_hash, is_admin)
VALUES 
('Super Admin', 'admin@ccny.edu', 'scrypt:32768:8:1$E8oHQhZc7z7QTryA$c43a9aa4f5ad4a5063e2b44b8ee7b29d006100b64c884a511217c17e7135d32d8b1573c5f3490191452c4e485db2708b0f6b1c1973b2f7fc629246ecb1860ba0', TRUE);