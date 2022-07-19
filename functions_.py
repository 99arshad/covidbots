import concurrent.futures
import datetime
import json
import math
import os
import random
import re
import string
from datetime import datetime, timedelta
from sys import platform as _platform
import cv2
import mysql.connector
import pandas as pd
import redis
import requests
from fake_headers import Headers
from fuzzywuzzy import fuzz
from pandas import json_normalize
from pytz import timezone

headers = Headers(headers=True)
BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")

if _platform == "linux" or _platform == "linux2":
    python_initial = "python3"
    options = {'quality': '100', "xvfb": ""}
    chrome = False
    client = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        socket_timeout=5,
    )


    def get_data_from_url(url):
        print(url)
        val = client.get(url)
        if val is None:
            response = requests.get(url, headers=headers.generate())
            if 'json' not in response.headers['Content-Type']:
                url = url.replace("cdn-api.co-vin.in", "api.cowin.gov.in")
                print(url)
                response = requests.get(url, headers=headers.generate())
                if 'json' not in response.headers['Content-Type']:
                    return {"error": "server overload! Try after some time"}
            client.setex(url, timedelta(seconds=3600), value=json.dumps(response.json()), )
            return response.json()
        else:
            return json.loads(val)


    def dbconnector():
        return mysql.connector.connect(
            host='localhost',
            user='website',
            password="arshad",
            port=3306,
            database='website',
            charset='utf8mb4'

        )


else:
    python_initial = "python"
    options = {'quality': '100'}

    chrome = True


    def get_data_from_url(url):
        print(url)
        response = requests.get(url, headers=headers.generate())
        if 'json' not in response.headers['Content-Type']:
            url = url.replace("cdn-api.co-vin.in", "api.cowin.gov.in")
            print(url)
            response = requests.get(url, headers=headers.generate())
            if 'json' not in response.headers['Content-Type']:
                return {"error": "server overload! Try after some time"}
        return response.json()


    def dbconnector():
        return mysql.connector.connect(
            host='localhost',
            user='root',
            port=3306,
            database='centersdatabase',
        )

domain = "vaccinele.ga"
domain2 = "covidke.tk"


def total_states_districts():
    return json.load(open(f"{BASE_DIR}/states_districts.json"))


def nowdate(num):
    return (datetime.now(timezone("Asia/Kolkata")) + timedelta(days=num)).strftime('%d-%m-%Y')


def notify_accepted_str(userdata):
    if userdata['ntfy'] == "pn":
        url = f"https://{domain}/p{userdata['pincode']}"
        slot_str = f"slots available in pincode: {userdata['pincode']}"
    elif userdata['ntfy'] == "ln":
        url = f"https://{domain}/ln{userdata['longitude']}lt{userdata['latitude']}"
        slot_str = f"slots available in your nearby area"
    elif userdata['ntfy'] == "ds":
        url = f"https://{domain}/s{userdata['state_id']}d{userdata['district_id']}"
        slot_str = f"slots available in {userdata['district_name']}, {userdata['state_name']}"
    else:
        url = f"https://{domain}/s{userdata['state_id']}d"
        slot_str = f"slots available in all districts of {userdata['state_name']}"

    if userdata['age'] == "*":
        age_str = f"for both age groups"
    else:
        age_str = f"for age {userdata['age']}+"

    if userdata['dose'] == "*":
        dose_str = f"dose 1 & 2"
    else:
        dose_str = f"dose {userdata['dose']}"

    return slot_str, age_str, dose_str, url


def unsubscribe(code):
    mydb = dbconnector()
    connection = mydb.cursor()
    connection.execute('UPDATE userdatabase SET status = %s WHERE code = %s ', ("off", code,))
    mydb.commit()
    mydb.close()


def fetch_elastic_data(ids):
    try:
        if type(ids) == str:
            ids = eval(ids)
        mydb = dbconnector()
        mycursor = mydb.cursor()
        if type(ids) == int:
            ids = [ids]
        if len(ids) == 1:
            mycursor.execute(f"SELECT * FROM centersdata WHERE center_id in (%s)", tuple(ids))
            single_center = mycursor.fetchone()
            if single_center is None:
                return {"error": "Not found"}
            datalist = {single_center[0]: eval(single_center[1])}
        else:
            mycursor.execute(f"SELECT * FROM centersdata WHERE center_id in {tuple(ids)}")
            datalist = {i[0]: eval(i[1]) for i in mycursor.fetchall()}
        return datalist
    except Exception as error:
        return {"error": str(error)}


def notification(rawdata, telebot=False, redditbot=False, sms=False, email=False, discordbot=False, whatsapp=False):
    mydb = dbconnector()
    connection = mydb.cursor()
    usertableheaders = ["ROWID INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT", "name VARCHAR(255)", "phone VARCHAR(255)",
                        "email VARCHAR(255)",
                        "chat_id VARCHAR(255)", "center_name VARCHAR(255)", "center_id INT",
                        "district_name VARCHAR(255)", "district_id VARCHAR(255)", "state_name VARCHAR(255)",
                        "state_id VARCHAR(255)",
                        "pincode INT", "latitude VARCHAR(255)", "longitude VARCHAR(255)",
                        "age VARCHAR(5)", "dose VARCHAR(3)", "timestamp INT", "ntfy VARCHAR(255)",
                        "status VARCHAR(255)",
                        "type VARCHAR(255)", "code VARCHAR(255)"]

    connection.execute("CREATE TABLE IF NOT EXISTS userdatabase ({})".format(",".join(usertableheaders)))

    userdata = {"name": "", "phone": "", "email": "", "chat_id": "", "center_name": "", "center_id": 0,
                "district_name": "", "district_id": "", "state_name": "", "state_id": "", "pincode": 0, "latitude": "",
                "longitude": "", "age": "*", "dose": "*",
                "timestamp": int((datetime.now(timezone("Asia/Kolkata")) + timedelta(days=-1)).timestamp()),
                "ntfy": "", "status": "on", "type": "",
                "code": ''.join(random.choices(string.ascii_letters + string.digits, k=6))}

    userdata.update(rawdata)
    if telebot:
        userdata.update({"type": "telegram"})
    if redditbot:
        userdata.update({"type": "reddit"})
    if sms:
        userdata.update({"type": "sms"})
    if email:
        userdata.update({"type": "email"})
    if discordbot:
        userdata.update({"type": "discord"})
    if whatsapp:
        userdata.update({"type": "whatsapp"})

    query = "INSERT  INTO userdatabase ({}) VALUES ({}) ".format(",".join(userdata.keys()),
                                                                 ",".join(["%s"] * len(userdata.keys())))
    val = tuple(userdata.values())
    connection.execute(query, val)  # Insertion in database
    mydb.commit()  # Commit
    mydb.close()
    return userdata


def fetch_json_single_district(district_id, startdate):
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district_id}" \
          f"&date={startdate}"
    response_json = get_data_from_url(url=url)
    if "error" in response_json:
        return response_json
    json_fetched = response_json['centers']

    if len(json_fetched) > 0:
        return json_fetched
    return None


def fetch_json_single_center(center_id, startdate):
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByCenter?center_id={center_id}&date={startdate}"
    response_json = get_data_from_url(url=url)
    if "centers" in response_json:
        return response_json['centers']
    return None


def centers_to_sms_table(centerslist):
    centers = centerslist
    dose1 = 0
    dose2 = 0

    for center in centers:
        for session in center['sessions']:
            if "available_capacity_dose1" in session:
                dose1 = dose1 + session["available_capacity_dose1"]
            if "available_capacity_dose2" in session:
                dose2 = dose2 + session["available_capacity_dose1"]
    dose1 = f"Dose 1 Slots:{dose1}\n\n" if dose1 > 0 else ""
    dose2 = f"Dose 2 Slots:{dose2}\n\n" if dose2 > 0 else ""

    table_str = f"Total no. of hospitals: {len(centers)}\n\n{dose1}{dose2}"
    return table_str


def centers_to_email_table(centerslist, dates):
    centers = centerslist

    table = []
    totaldates = list(dates.keys())

    for center in centers:
        row = {}
        if center['fee_type'] == "Paid":
            feespaid = '<i style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #dc3545;">Paid</i>'
        else:
            feespaid = ""
        vaccfees = "<br>"
        if 'vaccine_fees' in center:
            temp = [f"<small><strong>{vaccine['vaccine']} ₹{vaccine['fee']}</strong></small>" for vaccine in
                    center['vaccine_fees']]
            vaccfees = "<br>" + "<br>".join(temp) + "<br>"

        vaccine_center = f"{center['name']} {feespaid}{vaccfees}<small>{center['district_name']}, {center['state_name']} - {str(center['pincode'])}</small><br><span style='-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; font-size: 11px; font-size: .6875rem; font-weight: 600; padding: 2px 8px; line-height: 1; -webkit-border-radius: 3px; -moz-border-radius: 3px; -ms-border-radius: 3px; border-radius: 3px; float: left; border: 0px; color: #64736b; padding-left: 0px;float: left;border: 0px;color: #64736b;padding-left: 0px'>{center['from']} - {center['to']}</span>"

        row['Hospital Info'] = vaccine_center

        for date in totaldates:
            if center['center_id'] in dates[date]:
                for session in dates[date][center['center_id']]:
                    if session['date'] not in row:
                        row[session['date']] = ""
                    vaccine_text = f'<span style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; -ms-border-radius: 3px; font-family: inherit; font-size: inherit; cursor: pointer; padding: 7px 8px; font-size: 11px; font-size: .6875rem; line-height: 9px; font-weight: 500; display: block; outline: 0; -webkit-transition: all .3s; -moz-transition: all .3s; transition: all .3s; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; min-width: 60px; text-align: center; margin-top: 3px; color: red; background: transparent; border: 0px;color:black;background:transparent;border: 0px">{session["vaccine"]}</span>' if \
                        session['vaccine'] != "" else ""
                    dose1str = ""
                    dose2str = ""
                    if "available_capacity_dose1" in session:
                        if session['available_capacity_dose1'] != 0:
                            if session['available_capacity_dose1'] > 8:
                                dose1str = f'<i  style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #28a745;">{session["available_capacity_dose1"]}</i>'
                            else:
                                dose1str = f'<i style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #fd7e14;">{session["available_capacity_dose1"]}</i>'
                        else:
                            dose1str = '<i style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #dc3545;">Booked</i>'
                    if "available_capacity_dose2" in session:
                        if session['available_capacity_dose2'] != 0:
                            if session['available_capacity_dose2'] > 8:
                                dose2str = f'<i  style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #28a745;">{session["available_capacity_dose2"]}</i>'
                            else:
                                dose2str = f'<i style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #fd7e14;">{session["available_capacity_dose2"]}</i>'

                        else:
                            dose2str = '<i style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; -webkit-border-radius: 50px; -moz-border-radius: 50px; -ms-border-radius: 50px; border-radius: 50px; font-size: 12px; font-size: .75rem; color: #fff; font-style: normal; padding: 3px 12px 2px 12px; margin-left: 3px; position: relative; top: -3px; line-height: 1; background-color: #dc3545;">Booked</i>'
                    dosesstr = f'<div style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; display: -ms-flexbox; display: flex; -ms-flex-pack: center; justify-content: center;">{dose1str}{dose2str}</div>'
                    agestr = f'<span  style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; -ms-border-radius: 3px; font-family: inherit; font-size: inherit; cursor: pointer; padding: 7px 8px; font-size: 11px; font-size: .6875rem; line-height: 9px; font-weight: 500; display: block; outline: 0; -webkit-transition: all .3s; -moz-transition: all .3s; transition: all .3s; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; min-width: 60px; text-align: center; margin-top: 3px; color: red; background: transparent; border: 0px;color:red;background:transparent;border: 0px" >Age {str(session["min_age_limit"])}+</span>'
                    session_string_temp = f" {dosesstr}{vaccine_text}{agestr}"
                    row[session['date']] = row[session['date']] + session_string_temp
                if len(row) > 1:
                    table.append(row)

    dataframe = pd.DataFrame(json_normalize(table))
    totaldates = list(dataframe.columns)[1:]
    totaldates.sort(key=lambda changeddate: datetime.strptime(changeddate, '%d-%m-%Y'))
    totaldates = [datetime.strptime(datee, '%d-%m-%Y').strftime("%a %b %d %Y") for datee in totaldates]
    dataframe.columns = ["Hospital Info"] + totaldates
    dataframe = dataframe.reindex(dataframe.columns, axis=1)

    notavailable = '<div style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; display: -ms-flexbox; display: flex; -ms-flex-pack: center; place-content: center;"><span style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; -ms-border-radius: 3px; font-family: inherit; font-size: inherit; cursor: pointer; padding: 7px 8px; font-size: 11px; font-size: .6875rem; line-height: 9px; font-weight: 500; display: block; outline: 0; -webkit-transition: all .3s; -moz-transition: all .3s; transition: all .3s; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; min-width: 60px; text-align: center; margin-top: 3px;color: #afafaf;border:1px solid #afafaf;background:#f3f3f3;border-radius:1.25rem!important;">NA</span></div><span  style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; -ms-border-radius: 3px; font-family: inherit; font-size: inherit; cursor: pointer; padding: 7px 8px; font-size: 11px; font-size: .6875rem; line-height: 9px; font-weight: 500; display: block; outline: 0; -webkit-transition: all .3s; -moz-transition: all .3s; transition: all .3s; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; min-width: 60px; text-align: center; margin-top: 3px;color:red;background:transparent;border: 0px;top:-10px">‏</span><span style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; position: relative; top: -2px; -ms-border-radius: 3px; font-family: inherit; font-size: inherit; cursor: pointer; padding: 7px 8px; font-size: 11px; font-size: .6875rem; line-height: 9px; font-weight: 500; display: block; outline: 0; -webkit-transition: all .3s; -moz-transition: all .3s; transition: all .3s; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; min-width: 60px; text-align: center; margin-top: 3px;color:red;background:transparent;border: 0px;top:-10px">‏</span>'

    table_html = dataframe.to_html(index=False).replace('style="text-align: right;"', "")
    table_html = table_html.replace("NaN", notavailable).replace("&lt;", "<").replace("&gt;", ">")
    table_html = table_html.replace('class="dataframe"',
                                    'style="border-collapse: collapse; -webkit-font-smoothing: antialiased; '
                                    '-moz-osx-font-smoothing: grayscale; margin-bottom: 1rem; background-color: '
                                    'transparent; border: 1px solid #dee2e6; display: block; width: 100%; '
                                    'overflow-x: auto; -webkit-overflow-scrolling: touch; -ms-overflow-style: '
                                    '-ms-autohiding-scrollbar;" width="100%" bgcolor="transparent"')
    table_html = table_html.replace("<thead ",
                                    '<thead style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: '
                                    'grayscale;"')
    table_html = table_html.replace("<tr ",
                                    '<tr style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: '
                                    'grayscale;"')
    table_html = table_html.replace("<th ",
                                    '<th style="text-align: inherit; -webkit-font-smoothing: antialiased; '
                                    '-moz-osx-font-smoothing: grayscale; padding: .75rem; border-top: 1px solid '
                                    '#dee2e6; border: 1px solid #dee2e6; vertical-align: bottom; border-bottom: '
                                    '2px solid #dee2e6; border-bottom-width: 2px;" align="inherit" '
                                    'valign="bottom"')
    table_html = table_html.replace("<tbody ",
                                    '<tbody style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: '
                                    'grayscale;"')
    table_html = table_html.replace('<td ',
                                    '<td style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: '
                                    'grayscale; padding: .75rem; vertical-align: top; border-top: 1px solid '
                                    '#dee2e6; border: 1px solid #dee2e6;" valign="top"')
    table_html = table_html.replace('<br ',
                                    '<br style="-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: '
                                    'grayscale;"')
    table_html = table_html.replace('<small ',
                                    '<small style="font-size: 80%; font-weight: 400; -webkit-font-smoothing: '
                                    'antialiased; -moz-osx-font-smoothing: grayscale;"')

    return table_html


def centers_to_reddit_table(centerslist, dates):
    centers = centerslist
    table = []
    totaldates = list(dates.keys())
    strcount = 0
    broken = False
    for center in centers:

        row = {}
        vaccine_center = f"{center['name']}, {center['district_name']}, {center['state_name']} - {str(center['pincode'])} ( {center['from']} - {center['to']} ) [{center['fee_type']}]"
        row['vaccine_center'] = vaccine_center

        for date in totaldates:
            if center['center_id'] in dates[date]:
                for session in dates[date][center['center_id']]:
                    if session['date'] not in row:
                        row[session['date']] = ""
                    vaccine_text = "Vaccine : " + session['vaccine'] if session['vaccine'] != "" else ""
                    dose1str = ""
                    dose2str = ""
                    if "available_capacity_dose1" in session:
                        if session['available_capacity_dose1'] != 0:
                            dose1str = f"Avl_dose1 : **^( {str(session['available_capacity_dose1'])} )**"
                        else:
                            dose1str = 'D1:Booked'

                    if "available_capacity_dose2" in session:
                        if session['available_capacity_dose2'] != 0:
                            dose2str = f"Avl_dose1 : **^( {str(session['available_capacity_dose2'])} )**"
                        else:
                            dose2str = 'D2:Booked'
                    session_string_temp = f" ^({dose1str} {dose2str} [Age : {str(session['min_age_limit'])} +] {vaccine_text} )"
                    strcount = strcount + len(session_string_temp)
                    row[session['date']] = row[session['date']] + session_string_temp
        if len(row) > 1:
            table.append(row)
    table = table[:5]
    dataframe = pd.DataFrame(json_normalize(table))
    heading = list(dataframe)
    dates = heading[1:]
    dates.sort(key=lambda datetemp: datetime.strptime(datetemp, '%d-%m-%Y'))
    heading = [heading[0]] + dates

    result = dataframe[heading].to_numpy()
    table_rows = []
    for dataframe_row in result:
        dataframe_row = [str(i) if str(i) != "nan" else "^(N/A)" for i in dataframe_row]
        table_rows.append(("|".join(dataframe_row)))

    heading = ["Vaccination Centers"] + [f"^({date})" for date in heading[1:]]

    table_reddit = "|" + "|".join(heading) + "|\n" + "|:-" * len(heading) + "|\n" + "\n".join(table_rows)
    if broken:
        table_reddit = table_reddit + f"\n\nTable too long.For more information visit https://{domain}"
    return table_reddit


def centers_to_html_table(centerslist, dates):
    centers = centerslist
    table = []
    totaldates = list(dates.keys())
    paid = []
    free = []
    age = []
    dose1 = 0
    dose2 = 0
    vaccines = []
    for center in centers:
        row = {}

        feespaid = '<i class ="cancel">Paid</i>' if center['fee_type'] == "Paid" else ""
        vaccfees = "<br>"
        temp = []
        if 'vaccine_fees' in center:
            for vaccine in center['vaccine_fees']:
                vaccines.append(vaccine['vaccine'])
                temp.append(f"<small><strong>{vaccine['vaccine']} ₹{vaccine['fee']}</strong></small>")
                vaccfees = "<br>" + "<br>".join(temp) + "<br>"

        vaccine_center = f"{center['name']} {feespaid}{vaccfees}<small>{center['district_name']}, {center['state_name']} - {str(center['pincode'])}</small><br><span class='loc_open' style='float: left;border: 0px;color: #64736b;padding-left: 0px'>{center['from']} - {center['to']}</span>"

        row['Hospital Info'] = vaccine_center

        for date in totaldates:
            if center['center_id'] in dates[date]:
                for session in dates[date][center['center_id']]:
                    if session['date'] not in row:
                        row[session['date']] = ""
                    vaccine_text = f'<span class="btn_3 loc_open" style="color:black;background:transparent;border: 0px">{session["vaccine"]}</span>' if \
                        session['vaccine'] != "" else ""

                    dose1str = ""
                    if "available_capacity_dose1" in session:

                        if session['available_capacity_dose1'] != 0:
                            dose1 += 1
                            if session['available_capacity_dose1'] > 8:
                                dose1str = f'<i class="approved">{session["available_capacity_dose1"]}</i>'
                            else:
                                dose1str = f'<i class="pending">{session["available_capacity_dose1"]}</i>'
                        else:
                            dose1str = '<i class="cancel">Booked</i>'

                    dose2str = ""
                    if "available_capacity_dose2" in session:

                        if session['available_capacity_dose2'] != 0:
                            dose2 += 1
                            if session['available_capacity_dose2'] > 8:
                                dose2str = f'<i class="approved">{session["available_capacity_dose2"]}</i>'
                            else:
                                dose2str = f'<i class="pending">{session["available_capacity_dose2"]}</i>'
                        else:
                            dose2str = '<i class="cancel">Booked</i>'
                    dosesstr = f'<div class="d-flex justify-content-center">{dose1str}{dose2str}</div>'
                    age.append(str(session["min_age_limit"]) + "+")
                    agestr = f'<span class="btn_3 loc_open" style="color:red;background:transparent;border: 0px" >Age {str(session["min_age_limit"])}+</span>'
                    session_string_temp = f" {dosesstr}{vaccine_text}{agestr}"
                    row[session['date']] = row[session['date']] + session_string_temp
                    if center['fee_type'] == "Paid":
                        paid.append(center['center_id'])
                    else:
                        free.append(center['center_id'])
        if len(row) > 1:
            table.append(row)

    dataframe = pd.DataFrame(json_normalize(table))
    totaldates = list(dataframe.columns)[1:]
    totaldates.sort(key=lambda changeddate: datetime.strptime(changeddate, '%d-%m-%Y'))
    totaldates = [datetime.strptime(datee, '%d-%m-%Y').strftime("%a %b %d %Y") for datee in totaldates]
    dataframe.columns = ["Hospital Info"] + totaldates
    dataframe = dataframe.reindex(dataframe.columns, axis=1)
    sep = 5
    df_len = math.ceil(len(dataframe) / sep)
    list_of_dfs = [dataframe.loc[i * sep: (i + 1) * sep] for i in range(0, df_len)]

    notavailable = '<div class="d-flex justify-content-center"><span class="btn_3 rounded" style="color: #afafaf;border:1px solid #afafaf;background:#f3f3f3;border-radius:1.25rem!important;">NA</span></div><span class="btn_3 loc_open" style="color:red;background:transparent;border: 0px;top:-10px">‏</span><span class="btn_3 loc_open" style="color:red;background:transparent;border: 0px;top:-10px">‏</span>'
    table = list_of_dfs[0].to_html(index=False). \
        replace('style="text-align: right;"', ""). \
        replace("NaN", notavailable). \
        replace("&lt;", "<").replace("&gt;", ">"). \
        replace('class="dataframe"', 'class="table table-responsive table-striped table-bordered" ')

    age = list(set(age))
    vaccines = list(set(vaccines))
    free = len(list(set(free)))
    paid = len(list(set(paid)))

    data = {}
    data.update({"total": len(dataframe)})
    data.update({"showing": len(list_of_dfs[0])})
    data.update({"Age": age}) if len(age) > 0 else ""
    data.update({"Vaccines": vaccines}) if len(vaccines) > 0 else ""
    data.update({"Dose 1 slots": dose1}) if dose1 != 0 else ""
    data.update({"Dose 2 slots": dose2}) if dose2 != 0 else ""
    data.update({"Free centers": free}) if free != 0 else ""
    data.update({"Paid centers": paid}) if paid != 0 else ""

    return table, data


def choose_type(centers_data, session_data, telebot=False, redditbot=False, discordbot=False, notify=False):
    if telebot:
        return centers_to_html_table(centerslist=centers_data, dates=session_data)
    elif redditbot:
        return centers_to_reddit_table(centerslist=centers_data, dates=session_data)
    elif notify:
        return centers_data, session_data
    elif discordbot:
        return centers_to_html_table(centerslist=centers_data, dates=session_data)


def json_processing(json_data, age, capacity):
    session_data = {}

    if age != "*":
        if capacity == "available_capacity":
            for center in json_data:
                for session in center['sessions']:
                    if str(session['min_age_limit']) == age:
                        if session[capacity] > 0:
                            if session['date'] not in session_data:
                                session_data[session['date']] = {}
                            if center['center_id'] not in session_data[session['date']]:
                                session_data[session['date']][center['center_id']] = []
                            session_data[session['date']][center['center_id']].append(session)
        else:
            popelement = "available_capacity_dose1" if "2" in capacity else "available_capacity_dose2"
            for center in json_data:
                for session in center['sessions']:
                    session.pop(popelement)
                    if str(session['min_age_limit']) == age:
                        if session[capacity] > 0:
                            if session['date'] not in session_data:
                                session_data[session['date']] = {}
                            if center['center_id'] not in session_data[session['date']]:
                                session_data[session['date']][center['center_id']] = []
                            session_data[session['date']][center['center_id']].append(session)
    else:
        if capacity == "available_capacity":
            for center in json_data:
                for session in center['sessions']:
                    if session[capacity] > 0:
                        if session['date'] not in session_data:
                            session_data[session['date']] = {}
                        if center['center_id'] not in session_data[session['date']]:
                            session_data[session['date']][center['center_id']] = []
                        session_data[session['date']][center['center_id']].append(session)
        else:
            popelement = "available_capacity_dose1" if "2" in capacity else "available_capacity_dose2"
            for center in json_data:
                for session in center['sessions']:
                    session.pop(popelement)
                    if session[capacity] > 0:
                        if session['date'] not in session_data:
                            session_data[session['date']] = {}
                        if center['center_id'] not in session_data[session['date']]:
                            session_data[session['date']][center['center_id']] = []
                        session_data[session['date']][center['center_id']].append(session)

    reslen = len(session_data.keys())

    if reslen > 0:
        return json_data, session_data
    return None, None


def fetch_json(url, startdate, age, capacity):
    response_json = get_data_from_url(url=url)
    if "error" in response_json:
        return response_json
    json_fetched = response_json['centers']
    startdate_time = datetime.strptime(startdate, '%d-%m-%Y')
    reslen = len(json_fetched)
    if reslen != 0:
        json_processed, session_data = json_processing(json_data=json_fetched, age=age, capacity=capacity)
        if json_processed is None:
            startdate = (startdate_time + timedelta(7)).strftime('%d-%m-%Y')
            return fetch_json(url=url.split("date")[0] + f"date={startdate}", startdate=startdate, age=age,
                              capacity=capacity)
        return json_processed, session_data
    if age != "*":
        return {"error": f"Currently no slots are available for age {age}+"}
    else:
        return {"error": "Currently no slots are available for both age group."}


def fetch_json_states(districts_ids, startdate, age, capacity):
    startdate_time = datetime.strptime(startdate, '%d-%m-%Y')

    districts_json_fetched = []
    for district_id in districts_ids:
        single_district_data = fetch_json_single_district(district_id=district_id, startdate=startdate)

        if single_district_data is not None:
            districts_json_fetched.extend(single_district_data)

    reslen = len(districts_json_fetched)
    if reslen != 0:
        json_processed, session_data = json_processing(json_data=districts_json_fetched, age=age, capacity=capacity)
        if json_processed is None:
            startdate = (startdate_time + timedelta(7)).strftime('%d-%m-%Y')
            return fetch_json_states(districts_ids=districts_ids, startdate=startdate, age=age, capacity=capacity)
        return json_processed, session_data

    if age == 18:
        return {"error": "Currently no slots are available for age 18+"}
    elif age == 45:
        return {"error": "Currently no slots are available for  age 45+"}
    else:
        return {"error": "Currently no slots are available for both age group."}


def fetch_json_centers(center_ids, startdate, age, capacity):
    startdate_time = datetime.strptime(startdate, '%d-%m-%Y')

    center_json_fetched = []
    '''
    for center_id in center_ids:
        single_center_data = fetch_json_single_center(center_id=center_id, startdate=startdate)
        if single_center_data is not None:
            center_json_fetched.append(single_center_data)
    '''
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        tasks = {executor.submit(fetch_json_single_center, center_id, startdate) for center_id in center_ids}
        for task in concurrent.futures.as_completed(tasks):
            single_center_data = task.result()
            if single_center_data is not None:
                center_json_fetched.append(single_center_data)

    reslen = len(center_json_fetched)
    if reslen != 0:
        json_processed, session_data = json_processing(json_data=center_json_fetched, age=age, capacity=capacity)
        if json_processed is None:
            startdate = (startdate_time + timedelta(7)).strftime('%d-%m-%Y')
            return fetch_json_centers(center_ids=center_ids, startdate=startdate, age=age, capacity=capacity)
        return json_processed, session_data

    if age == 18:
        return {"error": "Currently no slots are available for age 18+"}
    elif age == 45:
        return {"error": "Currently no slots are available for  age 45+"}
    else:
        return {"error": "Currently no slots are available for both age group."}


def fetchCentersData(maindict, telebot=False, redditbot=False, discordbot=False, notify=False):
    age = "*"
    if 'age' in maindict:
        age = str(maindict['age'])

    capacity_var = "available_capacity"
    if 'dose' in maindict:
        dose = str(maindict['dose'])
        if dose == "1":
            capacity_var = "available_capacity_dose1"
        elif dose == "2":
            capacity_var = "available_capacity_dose1"

    if 'ntfy' not in maindict:
        if telebot:
            if maindict['choice'] == "pincode":
                maindict.update({"ntfy": "pn"})
            elif maindict['choice'] == "location":
                maindict.update({"ntfy": "ln"})
            elif maindict['district_name'] == "*":
                maindict.update({"ntfy": "st"})
            else:
                maindict.update({"ntfy": "ds"})
        else:
            if "pincode" in maindict:
                maindict.update({"ntfy": "pn"})
            elif 'latitude' and 'longitude' in maindict:
                maindict.update({"ntfy": "ln"})
            elif 'state_id' in maindict:
                if 'district_id' in maindict:
                    if maindict['district_id'] != "*":
                        maindict.update({"ntfy": "ds"})
                    else:
                        maindict.update({"ntfy": "st"})
                else:
                    maindict.update({"ntfy": "st"})
            elif 'district_id' in maindict:
                if maindict['district_id'] != "*":
                    maindict.update({"ntfy": "ds"})

    startdate = nowdate(0)
    if 'ntfy' in maindict:
        if maindict['ntfy'] == "pn":

            pincode = maindict['pincode']
            url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pincode}&date={startdate}"
            response_json = fetch_json(url=url, startdate=startdate, age=age, capacity=capacity_var)

        elif maindict['ntfy'] == "ln":
            lat = maindict['latitude']
            long = maindict['longitude']
            url = f"https://cdn-api.co-vin.in/api/v2/appointment/centers/public/findByLatLong?lat={lat}&long={long}"
            response_json = get_data_from_url(url=url)

            if "error" in response_json:
                return response_json

            center_ids = {center["center_id"] for center in response_json['centers']}
            response_json = fetch_json_centers(center_ids=center_ids, startdate=startdate, age=age,
                                               capacity=capacity_var)

        elif maindict['ntfy'] == "st":
            state_id = maindict['state_id']
            url = f"https://api.cowin.gov.in/api/v2/admin/location/districts/{state_id}"
            response_json = get_data_from_url(url=url)

            if "error" in response_json:
                return response_json

            districts_ids = {district['district_id'] for district in response_json['districts']}
            response_json = fetch_json_states(districts_ids=districts_ids, startdate=startdate, age=age,
                                              capacity=capacity_var)

        else:
            district_id = maindict['district_id']
            url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district_id}&date={startdate}"
            response_json = fetch_json(url=url, startdate=startdate, age=age, capacity=capacity_var)

        if "error" in response_json:
            return response_json

        centers_data, session_data = response_json
        return choose_type(centers_data=centers_data, session_data=session_data,
                           telebot=telebot, redditbot=redditbot, discordbot=discordbot, notify=notify)

    else:
        return {
            "error": "Enter proper parameters i.e pincode,location,district_id, state_id"}


def fuzzer(searchstring, bystate=False, bydistrict=False):
    json_total_states_districts = total_states_districts()
    ratio_dict = {}
    if bystate:
        for state_id, value in json_total_states_districts.items():
            ratio = fuzz.ratio(searchstring, value['state_name'])
            if ratio == 100:
                return [[ratio, [state_id, value['state_name'], "state"]]]
            ratio_dict.update({ratio: [state_id, value['state_name'], "state"]})
    if bydistrict:
        for state_id, value in json_total_states_districts.items():
            for district_data in value['districts']:
                ratio = fuzz.ratio(searchstring, district_data['district_name'])
                if ratio == 100:
                    return [[ratio, [district_data['district_id'], district_data['district_name'], state_id,
                                     value['state_name'], "district"]]]
                ratio_dict.update({ratio: [district_data['district_id'], district_data['district_name'], state_id,
                                           value['state_name'], 'district']})
    ratiolist = list(sorted(ratio_dict.items()))
    ratiolist.reverse()
    return ratiolist


def message_parser(messagestring):
    text = messagestring
    notify = False
    data = {"age": "*", "dose": "*"}
    for word in text.split():
        if "=" in word:
            k, v = word.split("=")
            data.update({k: v})
            text = text.replace(word, "")
        elif "+" in word:
            text = text.replace(word, "")
            word = re.search(r"\d+(\.\d+)?", word)
            if word is not None:
                word = word.group(0)
                if len(word) == 1:
                    data.update({"dose": word})
                if len(word) == 2:
                    data.update({"age": word})
        elif word.isdigit():
            text = text.replace(word, "")
            if len(word) == 1:
                data.update({"dose": word})
            if len(word) == 2:
                data.update({"age": word})
            if len(word) == 6:
                data.update({"pincode": word})
        elif "age" in word:
            num = re.search(r"\d+(\.\d+)?", word)
            if num is not None:
                num = num.group(0)
                if len(num) == 2:
                    data.update({"age": num})
                    text = text.replace(word, "")
        elif "pincod" in word:
            num = re.search(r"\d+(\.\d+)?", word)
            if num is not None:
                num = num.group(0)
                if len(num) == 6:
                    data.update({"pincode": num})
                    text = text.replace(word, "")
        elif "dos" in word:
            num = re.search(r"\d+(\.\d+)?", word)
            if num is not None:
                num = num.group(0)
                if len(num) == 1:
                    data.update({"dose": num})
                    text = text.replace(word, "")
        elif "@" in word:
            data.update({"email": word})
            text = text.replace(word, "")
        elif "notify" in word or "ntfy" in word:
            notify = True
            text = text.replace(word, "")

    place = " ".join(text.split())
    if len(place) > 2:
        fuzzres = fuzzer(bystate=True, bydistrict=True, searchstring=place)
        if len(fuzzres) > 0:
            if fuzzres[0][1][-1] == "state":
                data.update({"state_id": fuzzres[0][1][0]})
                data.update({"state_name": fuzzres[0][1][1]})
            elif fuzzres[0][1][-1] == "district":
                data.update({"district_id": fuzzres[0][1][0]})
                data.update({"district_name": fuzzres[0][1][1]})
                data.update({"state_id": fuzzres[0][1][2]})
                data.update({"state_name": fuzzres[0][1][3]})
    if "pincode" in data:
        data.update({"ntfy": "pn"})
    elif 'latitude' and 'longitude' in data:
        data.update({"ntfy": "ln"})
    else:
        if 'district_id' in data:
            data.update({"ntfy": "ds"})
        else:
            data.update({"ntfy": "st"})

    return data, notify


def crop_image(imgfile):
    try:
        img = cv2.imread(imgfile)
        _, thresh = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1, 255, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = contours[1]
        x, y, w, h = cv2.boundingRect(cnt)
        crop = img[y:y + h, x:x + w]
        cv2.imwrite(imgfile, crop)
    except Exception as error:
        print(error)



