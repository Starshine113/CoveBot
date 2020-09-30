alter table tickets add column ticket_closed boolean default true;

update info set schema_version = 14;