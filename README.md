# orovilledam.org
Oroville Dam Website.

## Installation
This is a Flask app (Python3).

``` sh
$ cd [your workspace]
$ git clone https://github.com/sgornick/orovilledam.org.git
$ cd orovilledam.org
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
``` 

Further deploy instructions will vary based on production system requirements.

For testing, use gunicorn:

``` sh
$ cd web_site
$ gunicorn dashboard:app
``` 

From a browser, access the app using: [http://localhost:8000](http://localhost:8000)

## License

MIT
