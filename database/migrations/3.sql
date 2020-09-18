create table if not exists interview_questions
(
    id int primary key,
    question text
);

update info set schema_version = 2;