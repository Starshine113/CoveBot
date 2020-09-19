alter table interviews add column welcome_message bigint not null default 0;

update info set schema_version = 4;
