create table if not exists starboard_messages
(
    message_id      bigint primary key,
    starboard_id    bigint
);

update info set schema_version = 7;
