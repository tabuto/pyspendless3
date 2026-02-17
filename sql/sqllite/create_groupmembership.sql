-- Creazione tabella GroupMembership / Invite
CREATE TABLE IF NOT EXISTS GroupMembership (
    id INTEGER PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES USER_GROUP(id),
    user_id TEXT REFERENCES User(id),
    invite_email TEXT NOT NULL,
    invited_by_user_id TEXT NOT NULL REFERENCES User(id),
    status TEXT NOT NULL CHECK(status IN ('pending','accepted','declined')),
    token TEXT NOT NULL
);
