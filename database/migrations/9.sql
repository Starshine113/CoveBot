create table if not exists pending_actions
(
    id              serial primary key,
    user_id         bigint,
    type            modaction not null,
    roles_to_remove bigint[],
    roles_to_add    bigint[],
    action_time     timestamp not null
);

update info set schema_version = 9;
