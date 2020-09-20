create table if not exists starboard
(
    id                      int primary key not null default 1, -- enforced only equal to 1
    channel                 bigint,
    star_limit              int,
    emoji                   text,
    constraint singleton    check (id = 1) -- enforce singleton table/row
);

insert into starboard (channel, star_limit, emoji) values (0, 1000, '⭐');

update info set schema_version = 6;
