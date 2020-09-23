create table if not exists highlights
(
    id      serial primary key,
    user_id bigint,
    word    text
);

update info set schema_version = 11;
