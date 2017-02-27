from pathlib import Path
from urllib import request
from lxml import html
from flask import Flask, jsonify, render_template
from datetime import datetime, timedelta
import json


def request_res_latest_json():
	# Scrape the latest available measurements from CA DWR CDEC.
	blank_val = '--'.rjust(10)
	url = 'http://cdec.water.ca.gov/cgi-progs/queryF?ORO'
	req = request.Request(url=url)
	with request.urlopen(req) as response:
		page = response.read()
		tree = html.fromstring(page)
	# There could be multiple tables in the page.
	# The table with hourly measurements has 14 rows and 15 colums.
	# The last row may be incomplete (blank values). Ignore these.
	res_elev_row = tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][td[2][text()!="{}"]]'.format(
			blank_val))[-1]
	flow_row = tree.xpath(
		'//div[@class="content_left_column"]/table[count(tr) = 14]/tr[count(td) = 15][td[6][text()!="{}"] and td[8][text()!="{}"]]'.format(
			blank_val, blank_val))[-1]
	res_elev_datetime = '{:%b %-d %-I%P}'.format(
		datetime.strptime(res_elev_row[0].xpath('text()')[0], '%m/%d/%Y %H:%M'))
	res_elev = float(res_elev_row[1].xpath('text()')[0])
	flow_datetime = '{:%b %-d %-I%P}'.format(
		datetime.strptime(flow_row[0].xpath('text()')[0], '%m/%d/%Y %H:%M'))
	outflow = int(flow_row[5].xpath('./text()')[0])
	inflow = int(flow_row[7].xpath('./text()')[0])

	data = {}
	data['timestamp_str'] = str(datetime.utcnow())
	data['res_elev_datetime'] = res_elev_datetime
	data['res_elev'] = res_elev
	data['flow_datetime'] = flow_datetime
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


app = Flask(__name__)


@app.route('/')
def index():
	data = res_latest()
	return render_template('index.html', data=data)


@app.route('/reslatest/', methods=['GET'])
def res_latest_json():
	return jsonify(res_latest())
