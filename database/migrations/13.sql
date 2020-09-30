create table if not exists tickets_config
(
    id                      int primary key not null default 1, -- enforced only equal to 1
    listen_channel          bigint,
    listen_message          bigint,
    listen_reaction         text,
    welcome_message         text,
    constraint singleton    check (id = 1) -- enforce singleton table/row
);

insert into tickets_config (listen_channel, listen_message, listen_reaction, welcome_message) values (0, 0, '📩', '{mention} Welcome\n@here');

update info set schema_version = 13;
