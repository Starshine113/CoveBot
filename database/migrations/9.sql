create table if not exists pending_actions
(
    id              serial primary key,
    type            modaction not null,
    roles_to_remove bigint[],
    roles_to_add    bigint[],
    action_time     timestamp not null,
    user_id         bigint
);

update info set schema_version = 9;
