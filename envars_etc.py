from time import asctime
from os import getenv

# env vars
token = getenv('token')
whitelist = getenv('wl_path')
adminlist = getenv('al_path')

sql_host = getenv('host')
sql_user_name = getenv('user')
sql_password = getenv('SQL_password')
sql_db_name = getenv('db_name')

def crash_report(exception):
    with open('crash_report.txt', 'w') as crash:
        crash.write(f'{asctime()}\n{str(exception)}')

        print('[ERROR] Check the crash reports')
        quit(1)

def remove_linebreaks(lines):
    return [i.replace('\n', '') for i in list(lines.readlines())]
