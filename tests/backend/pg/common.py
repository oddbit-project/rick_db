create_table = "create table if not exists animal(id_animal serial not null primary key, name varchar);"
create_fk_table = "create table if not exists animal_type(fk_animal int not null references animal, labels varchar);"
create_schema = "create schema myschema;"
create_schema_table = "create table if not exists myschema.aliens(id_alien serial not null primary key, name varchar);"
create_view = "create view list_animal as select * from animal;"
create_schema_view = (
    "create view myschema.list_aliens as select * from myschema.aliens;"
)
create_group = "create group staff;"
add_group = "alter group staff add user {user}"
drop_group = "drop group staff"
create_identity_table = "create table if not exists foo(id_foo int generated always as identity, name varchar);"
