# orodamcdec
Oroville Dam 

## Synopsis
Extract latest reading from CA DWR CDEC website for ORO (Oroville DAM), expose
as JSON.

## Installation
This is a Flask app (Python3).

``` sh
$ cd [your workspace]
$ git clone https://github.com/pubdataca/orodamcdec.git
$ cd orodamcdec
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
``` 

Further deploy instructions will vary based on production system requirements.

For testing, use gunicorn:

``` sh
$ gunicorn orodamcdec:app
``` 

From a browser, access the app using: [http://localhost:8000/orodamcdec](http://localhost:8000/orodamcdec)

## License

MIT
