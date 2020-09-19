alter table tickets drop constraint tickets_pkey;
alter table tickets add column id serial;
alter table tickets add primary key (id);

update info set schema_version = 5;
