create table if not exists blacklisted_channels
(
    channel_id bigint
);

update info set schema_version = 8;
