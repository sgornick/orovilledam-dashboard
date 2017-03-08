from pathlib import Path
from urllib import request
from lxml import html
from flask import Flask, Response, request as flask_request, jsonify, render_template, abort
from werkzeug.contrib.atom import AtomFeed
from selenium import webdriver
from datetime import datetime, timedelta
import json
import os
import pytz


def request_res_latest_json():
	# Scrape the latest available measurements from CA DWR CDEC.
	blank_val = '--'.rjust(10)
	data = {}
	url = 'http://cdec.water.ca.gov/cgi-progs/queryF?ORO'
	req = request.Request(url=url)
	with request.urlopen(req) as response:
		page = response.read()
	tree = html.fromstring(page)
	# There could be multiple tables in the page.
	# The table with hourly measurements has 14 rows and 15 colums.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	res_elev_row = tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"]]'.format(
			blank_val))[-1]
	flow_row = tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][position() > 2][td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val))[-1]
	res_elev_datetime = '{:%b %-d %-I%P}'.format(
		datetime.strptime(res_elev_row[0].xpath('text()')[0], '%m/%d/%Y %H:%M'))
	res_elev = float(res_elev_row[1].xpath('text()')[0])
	flow_datetime = '{:%b %-d %-I%P}'.format(
		datetime.strptime(flow_row[0].xpath('text()')[0], '%m/%d/%Y %H:%M'))
	outflow = int(flow_row[5].xpath('./text()')[0])
	inflow = int(flow_row[7].xpath('./text()')[0])
	data['timestamp_str'] = str(datetime.utcnow())
	data['res_elev_datetime'] = res_elev_datetime
	data['res_elev'] = res_elev
	data['flow_datetime'] = flow_datetime
	data['inflow'] = inflow
	data['outflow'] = outflow
	return data


def request_gauges_latest_json():
	# Scrape the latest available measurements from CA DWR CDEC.
	blank_val = '--'.rjust(10)
	data = {}
	PT = pytz.timezone('America/Los_Angeles')  # Pacific Timezone
	url = 'http://cdec.water.ca.gov/cgi-progs/queryF?ORO'
	req = request.Request(url=url)
	with request.urlopen(req) as response:
		page = response.read()
	tree = html.fromstring(page)
	# There could be multiple tables in the page.
	# The table with hourly measurements has 14 rows and 15 colums.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	row = tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"] and td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val, blank_val))[-1]
	row_datetime = datetime.strptime(row[0].xpath('text()')[0], '%m/%d/%Y %H:%M')
	row_datetime = PT.localize(row_datetime)
	datetime_str = '{:%B %-d, %Y %-I%P} {}'.format(
		row_datetime, row_datetime.tzname())
	res_elev = float(row[1].xpath('text()')[0])
	outflow = int(row[5].xpath('./text()')[0])
	inflow = int(row[7].xpath('./text()')[0])
	data['timestamp_str'] = str(datetime.utcnow())
	data['datetime'] = datetime_str
	data['res_elev'] = res_elev
	data['inflow'] = inflow
	data['outflow'] = outflow
	return data


def res_latest():
	site_root = Path(__file__).parent
	path = Path(site_root, "data", "reslatest.json")
	data = {}
	if path.is_file():
		with path.open("r") as data_file:
			data = json.load(data_file)
	# If more than a minute old, get the latest.
	if 'timestamp_str' not in data or \
		abs((datetime.utcnow() - datetime.strptime(data['timestamp_str'], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()) >= 60:
		data = request_res_latest_json()
		with path.open('w') as data_file:
			json.dump(data, data_file)
	return data


def gauges_latest():
	site_root = Path(__file__).parent
	path = Path(site_root, "data", "gaugeslatest.json")
	data = {}
	if path.is_file():
		with path.open("r") as data_file:
			data = json.load(data_file)
	# If more than a minute old, get the latest.
	if 'timestamp_str' not in data or \
		abs((datetime.utcnow() - datetime.strptime(data['timestamp_str'], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()) >= 60:
		data = request_gauges_latest_json()
		with path.open('w') as data_file:
			json.dump(data, data_file)
	return data


def sync_gauges_json(last_datetime_str):
	# If json file in data directory is stale, delete it so will get refreshed.
	data = {}
	site_root = Path(__file__).parent
	path = Path(site_root, "data", "gaugeslatest.json")
	if path.is_file():
		with path.open("r") as data_file:
			data = json.load(data_file)
		if last_datetime_str != data['datetime']:
			os.remove(str(path))


app = Flask(__name__)


@app.route('/')
def index():
	data = res_latest()
	return render_template('index.html', data=data)

@app.route('/gauges/')
def gauges():
	data = gauges_latest()
	return render_template('gauges.html', data=data)

@app.route('/gaugeslatest/', methods=['GET'])
def gauges_latest_json():
	return jsonify(gauges_latest())

@app.route('/reslatest/', methods=['GET'])
def res_latest_json():
	return jsonify(res_latest())

@app.route('/latest/', methods=['GET'])
@app.route('/latest/<filename>.<file_ext>', methods=['GET'])
@app.route('/latest/<filename>', methods=['GET'])
def latest(filename='latest', file_ext='png'):
	url = 'https://orovilledam.org/gauges'
	output_types = {
		'png': 'image/png',
	}
	if file_ext and file_ext.lower() not in output_types:
		abort(404)
	driver = webdriver.PhantomJS(executable_path="/usr/bin/phantomjs", service_log_path=os.path.devnull)
	driver.set_window_size(600, 350)
	driver.get(url)
	png = driver.get_screenshot_as_png()
	driver.quit()
	return (Response(png, mimetype="image/png"))


@app.route('/feed/', methods=['GET'])
@app.route('/rss/', methods=['GET'])
def feed():
	blank_val = '--'.rjust(10)
	rows = []
	url = 'https://cdec.water.ca.gov/cgi-progs/queryF?ORO'
	PT = pytz.timezone('America/Los_Angeles')  # Pacific Timezone
	req = request.Request(url=url)
	with request.urlopen(req) as response:
		page = response.read()
	feed = AtomFeed('Recent entries', feed_url=flask_request.url, url=flask_request.url_root)
	tree = html.fromstring(page)
	# There could be multiple tables in the page.
	# The table with hourly measurements has 14 rows and 15 colums.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	last_datetime_str = None
	for row in tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"] and td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val, blank_val)):
		data = {}
		row_datetime = datetime.strptime(row.xpath('td')[0].xpath('text()')[0], '%m/%d/%Y %H:%M')
		row_datetime = PT.localize(row_datetime)
		data['entryTitle'] = '{:%B %-d, %Y %-I%P} {}'.format(row_datetime, row_datetime.tzname())
		last_datetime_str = data['entryTitle']
		data['entryText'] = '- Lake Level: {:,.2f} ft, Storage: {:,d} af, Outflow: {:,d} cfps, Inflow: {:,d} cfps https://OrovilleDam.org'.format(
			float(row.xpath('td')[1].xpath('text()')[0]),
			int(row.xpath('td')[3].xpath('text()')[0]),
			int(row.xpath('td')[5].xpath('text()')[0]),
			int(row.xpath('td')[7].xpath('text()')[0]))
		feed.add(
		   data["entryTitle"],
		   data["entryText"],
		   id='https://cdec.water.ca.gov/cgi-progs/queryF?ORO#{:%Y%m%d%H%M%S}'.format(row_datetime),
		   content_type='text',
		   author='California Dept of Water Resources https://cdec.water.ca.gov/cgi-progs/queryF?ORO',
		   url='https://cdec.water.ca.gov/cgi-progs/queryF?ORO',
		   updated=row_datetime,
		   published=row_datetime)
    # After doing a /feed, if there's a new entry, /gauge will be accessed.
    # But that could return a stale view since the gauge json was recent.
    # So if /feed has a newer reading than the gauge json, purge it so it will be recreated next time, fresh.
	sync_gauges_json(last_datetime_str)
	return feed.get_response()
