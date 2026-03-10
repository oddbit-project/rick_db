create_table = (
    "create table animal(id_animal integer primary key autoincrement, name varchar);"
)
create_index = "create index idx01 on animal(id_animal)"
create_view = "create view list_animals as select * from animal"
