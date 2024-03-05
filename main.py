from flask import Flask, render_template, request
from utils import MAPPING, lookup_date_range_both_ways
from datetime import datetime, timedelta

app = Flask(__name__,
            static_url_path='/static/', 
            static_folder='static')

@app.route('/')
def hello(name=None):
    return render_template('index.html')

@app.route('/results')
def results(name=None):
    # Conversion des codes gares
    start = []
    if request.args.get('start1') != "":
        start.append((MAPPING[request.args.get('start1')]))
    if request.args.get('start2') != "":
        start.append((MAPPING[request.args.get('start2')]))
    end = []
    if request.args.get('end1') != "":
        end.append((MAPPING[request.args.get('end1')]))
    if request.args.get('end2') != "":
        end.append((MAPPING[request.args.get('end2')]))

    result = (
        lookup_date_range_both_ways(
            start,
            end,
            request.args.get("trip-start"),
            request.args.get("trip-end"),
            request.args.get("captcha_datadome"),
        )
        .reset_index()
        .drop("index", axis=1)
    )
    if len(result.index) == 0:
        return("No results.")
    rg = result.groupby(['date', 'day', 'hour', 'direction', 'orig', 'dest']).agg(total_seats=('seats', 'sum')).reset_index()

    str_events = ""
    for index, row in rg.iterrows():
        if row['direction'] == 'outbound':
            color = "blueviolet"
        else:
            color = "orangered"
        str_events += f"""
            {{
            day: {(row['date'] - (datetime.strptime(request.args.get('trip-start'), '%Y-%m-%d')).date()).days+1},
            hour: {row['hour']},
            title: '{row['orig'][0:10]} > {row['dest'][0:10]}',
            alignment: 'left',
            color: '{color}'
            }},
        """

    start_dt = datetime.strptime(request.args.get('trip-start'), '%Y-%m-%d')
    end_dt = datetime.strptime(request.args.get('trip-end'), '%Y-%m-%d')

    delta = timedelta(days=1)

    # store the dates between two dates in a list
    days = []

    while start_dt <= end_dt:
        # add current date to list by converting  it to iso format
        days.append(start_dt.date().strftime('%A %d/%m'))
        # increment start date by timedelta
        start_dt += delta

    return render_template('results.html', days=days, str_events=str_events)
