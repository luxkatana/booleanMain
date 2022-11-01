CREATE TABLE IF NOT EXISTS
autorespond
(
    guildID bigint,
    listen boolean,
    trigger_text text,
    respond text
);