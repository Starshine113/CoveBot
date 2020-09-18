create type modaction as enum ('warn', 'mute', 'pause', 'hardmute', 'kick', 'tempban', 'ban');

create table if not exists interviews
(
    user_id             bigint primary key,
    channel_id          bigint,
    current_question    int default 0
);

create table if not exists notes
(
    id      serial primary key,
    user_id bigint,
    set_by  bigint,
    reason  text,
    created timestamp not null default (current_timestamp at time zone 'utc')
);

create table if not exists modactions
(
    id      serial primary key,
    user_id bigint,
    mod_id  bigint,
    type    modaction,
    reason  text,
    created timestamp not null default (current_timestamp at time zone 'utc')
);

create table if not exists info
(
    id                      int primary key not null default 1, -- enforced only equal to 1
    schema_version          int,
    constraint singleton    check (id = 1) -- enforce singleton table/row
);

insert into info (schema_version) values (1);