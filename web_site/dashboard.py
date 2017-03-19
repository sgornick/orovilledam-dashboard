from pathlib import Path
from urllib import request
from urllib.error import URLError, HTTPError
from lxml import html, etree
from flask import Flask, Response, request as flask_request, jsonify, render_template, send_file, abort
from werkzeug.contrib.atom import AtomFeed
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import io
import json
import os
import pytz
import logging


def request_res_latest_json():
	# Scrape the latest available measurements from CA DWR CDEC.
	blank_val = '--'.rjust(10)
	data = {}
	# Populate at least what is needed to return if there is an error or exception.
	data['res_elev'] = 0
	data['inflow'] = 0
	data['outflow'] = 0
	page = request_cdec_hourly_page()
	if page is None:
		return data
	# There could be multiple tables in the page.
	# The table with hourly measurements has either 14 or 15 rows and exactly 15 columns.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	xpath_predicate = '//div[@class="content_left_column"]/table[count(tr) >= 14 and count(tr) <= 15]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"]]'.format(
			blank_val)
	rows = parse_page_table('res_elev', xpath_predicate, page)
	if rows is None:
		return data
	res_elev_row = rows[-1]
	xpath_predicate = '//div[@class="content_left_column"]/table[count(tr) >= 14 and count(tr) <= 15]/tr[count(td) = 15][position() > 2][td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val)
	rows = parse_page_table('flow', xpath_predicate, page)
	if rows is None:
		return data
	flow_row = rows[-1]
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
	# Populate at least what is needed to return if there is an error or exception.
	data['res_elev'] = 0
	data['inflow'] = 0
	data['outflow'] = 0
	PT = pytz.timezone('America/Los_Angeles')  # Pacific Timezone
	page = request_cdec_hourly_page()
	if page is None:
		return data
	# There could be multiple tables in the page.
	# The table with hourly measurements has either 14 or 15 rows and exactly 15 colums.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	xpath_predicate = '//div[@class="content_left_column"]/table[count(tr) >= 14 and count(tr) <= 15]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"] and td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val, blank_val)
	rows = parse_page_table('gauge', xpath_predicate, page)
	if rows is None:
		return data
	row = rows[-1]
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
	path = Path(site_root, 'data', 'reslatest.json')
	data = {}
	if path.is_file():
		with path.open('r') as data_file:
			data = json.load(data_file)
	# If more than a minute old, get the latest.
	if 'timestamp_str' not in data or \
		abs((datetime.utcnow() - datetime.strptime(data['timestamp_str'], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()) >= 60:
		latest_data = request_res_latest_json()
		if 'timestamp_str' in latest_data:
			with path.open('w') as data_file:
				json.dump(latest_data, data_file)
			data = latest_data
		elif 'timestamp_str' not in data:
			# We have neither old or new, so use the zero/default values.
			data = latest_data
	return data


def gauges_latest():
	site_root = Path(__file__).parent
	path = Path(site_root, 'data', 'gaugeslatest.json')
	data = {}
	if path.is_file():
		with path.open('r') as data_file:
			data = json.load(data_file)
	# If more than a minute old, get the latest.
	if 'timestamp_str' not in data or \
		abs((datetime.utcnow() - datetime.strptime(data['timestamp_str'], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()) >= 60:
		latest_data = request_gauges_latest_json()
		if 'timestamp_str' in latest_data:
			with path.open('w') as data_file:
				json.dump(latest_data, data_file)
			data = latest_data
		elif 'timestamp_str' not in data:
			# We have neither old or new data, so use the zero/default values.
			data = latest_data
	return data


def sync_gauges_json(last_datetime_str):
	# If json file in data directory is stale, delete it so will get refreshed.
	data = {}
	site_root = Path(__file__).parent
	path = Path(site_root, 'data', 'gaugeslatest.json')
	if path.is_file():
		with path.open('r') as data_file:
			data = json.load(data_file)
		if last_datetime_str != data.get('datetime'):
			os.remove(str(path))


def save_debug_data(data):
	site_root = Path(__file__).parent
	path = Path(site_root, 'data', 'debug-data-{:%Y%m%d%H%M%S}'.format(datetime.utcnow()))
	with path.open('w') as debug_file:
		debug_file.write(data)
		logging.warning('Wrote debug data file: {}'.format(path))


def request_cdec_hourly_page():
	url = 'http://cdec.water.ca.gov/cgi-progs/queryF?ORO'
	req = request.Request(url=url)
	attempt = 0
	page = None
	while attempt < 3:
		attempt += 1
		try:
			with request.urlopen(req) as response:
				page = response.read()
				break
		except (URLError, HTTPError) as e:
			logging.warning('The following error has occurred: {}'.format(repr(e)))
			break
		except ConnectionResetError as e:
		   logging.warning('The following error has occurred: {}'.format(repr(e)))
	return page


def parse_page_table(label, xpath_predicate, page):
	try:
		tree = html.fromstring(page)
	except etree.XMLSyntaxError as e:
		# Bad markup returned.
		logging.warning('The following error has occurred: {}'.format(repr(e)))
		return None
	rows = tree.xpath(xpath_predicate)
	if len(rows) < 1:
		# Unexpected data somewhere.
		logging.warning('The following error has occurred: Expected {} rows, found only: {} rows'.format(
			label, len(rows)))
		save_debug_data(str(page))
		return None
	return rows


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=True)

@app.route('/')
def index():
	data = res_latest()
	data['analytics_id'] = app.config['ANALYTICS_ID']
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
	url = 'https://phantomjscloud.com/api/browser/v2/{}/?request={{url:%22https://orovilledam.org/gauges/%22,renderType:%22png%22,renderSettings:{{viewport:{{width:600,height:350}}}}}}'.format(
		app.config['PHANTOMJSCLOUD_API_KEY'])
	output_types = {
		'png': 'image/png',
	}
	if file_ext and file_ext.lower() not in output_types:
	   abort(404)
	req = request.Request(url=url)
	with request.urlopen(req) as response:
		mimetype = response.headers['Content-Type']
		image_data = io.BytesIO(response.read())
	return send_file(
		image_data,
		attachment_filename=secure_filename('{}.{}'.format(filename, file_ext)),
		mimetype=mimetype)


@app.route('/feed/', methods=['GET'])
@app.route('/rss/', methods=['GET'])
def feed():
	blank_val = '--'.rjust(10)
	PT = pytz.timezone('America/Los_Angeles')  # Pacific Timezone
	feed = AtomFeed('Recent entries', feed_url=flask_request.url, url=flask_request.url_root)
	page = request_cdec_hourly_page()
	if page is None:
		return feed.get_response()
	# There could be multiple tables in the page.
	# The table with hourly measurements has either 14 or 15 rows and exactly 15 colums.
	# The first two rows are for the title, ignore that.
	# The last row may be incomplete (blank values). Ignore these.
	last_datetime_str = None
	xpath_predicate = '//div[@class="content_left_column"]/table[count(tr) >= 14 and count(tr) <= 15]/tr[count(td) = 15][position() > 2][td[2][text()!="{}"] and td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val, blank_val)
	rows = parse_page_table('feed', xpath_predicate, page)
	if rows is None:
		return feed.get_response()
	for row in rows:
		data = {}
		row_datetime = datetime.strptime(row.xpath('td')[0].xpath('text()')[0], '%m/%d/%Y %H:%M')
		row_datetime = PT.localize(row_datetime)
		last_datetime_str = '{:%B %-d, %Y %-I%P} {}'.format(row_datetime, row_datetime.tzname())
		data['entryTitle'] = last_datetime_str
		data['entryText'] = 'Lake Level: {:,.2f} ft, Inflow: {:,d} cfps, Outflow: {:,d} cfps'.format(
			float(row.xpath('td')[1].xpath('text()')[0]),
			int(row.xpath('td')[7].xpath('text()')[0]),
			int(row.xpath('td')[5].xpath('text()')[0]))
		feed.add(
		   data['entryTitle'],
		   data['entryText'],
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
