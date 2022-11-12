CREATE TABLE IF NOT EXISTS
checklists(
    ID int AUTO_INCREMENT,
    authorID BIGINT,
    guildID BIGINT,
    note_text VARCHAR(90),
    PRIMARY KEY (ID)
);