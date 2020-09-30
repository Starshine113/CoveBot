create table if not exists selfroles
(
    role_id bigint primary key
);

update info set schema_version = 15;
