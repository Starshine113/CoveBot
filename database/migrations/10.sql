alter table modactions add column duration text;

update info set schema_version = 10;
