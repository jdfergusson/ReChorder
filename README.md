## Installation

Installation steps taken on a reasonably fresh install of Ubuntu 20.04 
(but one with a working python 3.8 installation that can be run by just 
executing `python`)

Note these steps are for development installation, not deployment.

```bash
sudo apt install python3-django python3-psycopg2 postgresql postgresql-contrib
sudo -u postgres -i
psql
```

Now in the postgres terminal

```
CREATE USER <psql_user>;
\password <psql_user>
[ ENTER THE PASSWORD AS PROMPTED ]
CREATE DATABASE rechorder OWNER <psql_user>; 
``` 

Then edit the database connection settings in `rechorder/rechorder/settings.py`
to use the psql user and password as entered above.

Then 
```bash
cd <project_location>/rechorder
python ./manage.py migrate
python ./manage.py runserver
``` 

Then navigate to `localhost:8000/songview` in a browser


