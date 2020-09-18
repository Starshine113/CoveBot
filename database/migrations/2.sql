create table if not exists tickets
(
    channel_id  bigint primary key,
    user_id     bigint
);

update info set schema_version = 2;