@echo off
set token=
set wl_path=user_lists\whitelist.txt
set al_path=user_lists\adminlist.txt

set host=127.0.0.1
set user=postgres
set SQL_password=root
set db_name=stock

python main.py
