#!/usr/bin/env bash
export token=''
export wl_path='user_lists/whitelist.txt'
export al_path='user_lists/adminlist.txt'

export host='127.0.0.1'
export user='postgres'
export SQL_password='root'
export db_name='stock'

python3 main.py
