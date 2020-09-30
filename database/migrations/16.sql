alter table pending_actions add column add_to_log boolean;

update info set schema_version = 16;
