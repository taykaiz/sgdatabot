
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from telepot.delegate import per_chat_id, create_open, pave_event_space, include_callback_query_chat_id
import dataset
import geopy.distance
from geopy.geocoders import Nominatim
import requests
from SVY21 import SVY21
import time
import datetime
import csv
import json
import random

BOT_NAME = "@YOUR_BOT_NAME"
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN
DATAMALL_TOKEN = "YOUR_DATAMALL_TOKEN"

DATABASE_PATH = "sqlite:///SGdataBot.db"
HDB_CARPARK_CSV_PATH = "datagov/hdb-carpark-information.csv"
LTADATAMALL_STOPS_JSON_PATH = "ltadatamall/stops.json"
# defined in meters
BUSSTOP_SEARCH_DIST = 250

data_gov_headers = {}
DATAGOV_URI = "https://api.data.gov.sg/v1/"
ltadatamall_headers = {
    'AccountKey': DATAMALL_TOKEN,
    'accept': 'application/json'
}
LTADATAMALL_URI = "http://datamall2.mytransport.sg/ltaodataservice/"
rain_comments = [
    "Wah better bring umbrella!",
    "Wah lao, who stun  my Gortex jacket?",
    "Ti oh oh, beh loh ho. Please prepare your umbrella hor.",
    "Happy rainy day! Free water from the sky.",
    "Wah siao liao, heavy thunderstorm. You might need to put on Phua Chu Kang's yellow boots to protect yourself from the rain!!",
    "Don't say good things never share. Got free showers outside!",
    "Thunderstorm! You better be careful. Don't hide under the trees ah!",
    "Once in 50 years ponding again!",
    "Dayung sampan, dayung sampan, ...",
    "Time to roll out the sampans!!",
    "Rain, rain, go away. Come again another day ...",
    "Save money don't need wash car liao",
    "Wah population of cats and dogs going to spike again today."
]
#Global flags and variables for common alerts
rain_alert_enable_flag = True
train_alert_enable_flag = True
prev_train_msg_text = "none"


def getDatabase():
    db = dataset.connect(DATABASE_PATH)
    return db


def isList(table):
    try:
        for i in table:
            return True
    except:
        return False
    return False


def isAPIhealthy(request):
    status = False
    try:
        if request.json()['api_info']['status'] == 'healthy':
            status = True
        else:
            status = False
    except:
        status = False
    #        if not r.json()['items'] or  not r.json()['items'][0]:
    #                status = False

    return status


def is2hrForecastAreaValid(area):
    url = DATAGOV_URI + "environment/2-hour-weather-forecast"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        return False
    for i in req.json()['items'][0]['forecasts']:
        if i['area'] == area:
            return True
    return False


def poll2hrForecast(area):
    forecast = 'invalid'
    end_time = '00:00'
    url = DATAGOV_URI + "environment/2-hour-weather-forecast"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output, forecast, end_time
    try:
        for i in req.json()['items'][0]['forecasts']:
            if i['area'] == area:
                start_period = req.json()['items'][0]['valid_period']['start']
                start_period_idx = start_period.find('T')
                start_time = start_period[start_period_idx + 1:start_period_idx + 6]
                end_period = req.json()['items'][0]['valid_period']['end']
                end_period_idx = end_period.find('T')
                end_time = end_period[end_period_idx + 1:end_period_idx + 6]
                forecast = i['forecast']
                output = "*%s* 2Hr Forecast (_%s - %s_):\n```%s```" % (area, start_time, end_time, forecast)
                return output, forecast, end_time
    except:
        output = "API is down!"
        return output, forecast, end_time
    # if reached this point, area is not found
    output = "Area *%s* not found. Please select enter one of the following valid areas:\n" % area
    area_list = ""
    first = True
    for i in req.json()['items'][0]['forecasts']:
        if first:
            first = False
            area_list = area_list + i['area']
        else:
            area_list = area_list + ", " + i['area']
    output = output + area_list
    return output, forecast, end_time


def rainUpdate(title_msg, chat_id):
    msg_output = title_msg
    alert_output = ""
    rain_flag = False
    db = getDatabase()
    if db is not False:
        table_name = str(chat_id) + "_arealist"
        table = db[table_name]
        if isList(table) is True:
            for alerts in table:
                output, forecast, end_time = poll2hrForecast(alerts['area'])
                # check for invalid API
                if forecast == 'invalid':
                    msg_output = "none"
                    return msg_output
                if forecast != alerts['prev_forecast']:
                    table.delete(area=alerts['area'])
                    table.insert(dict(area=alerts['area'], prev_forecast=forecast))
                    if 'Showers' in forecast or 'Rain' in forecast or 'Thunderstorm' in forecast:
                        rain_flag = True
                        alert_output = alert_output + output + "\n"
    if rain_flag is False:
        msg_output = "none"
    else:
        max_idx = len(rain_comments) - 1
        idx = random.randint(0, max_idx)
        msg_output = msg_output + alert_output + rain_comments[idx]

    return msg_output


def forcedRainUpdate(chat_id):
    msg_output = "`Forced Update`\n"
    forecast = ""
    db = getDatabase()
    if db is not False:
        table_name = str(chat_id) + "_arealist"
        table = db[table_name]
        if isList(table) is True:
            for alerts in table:
                output, forecast, end_time = poll2hrForecast(alerts['area'])
                table.delete(area=alerts['area'])
                table.insert(dict(area=alerts['area'], prev_forecast="none"))
                msg_output = msg_output + output + "\n"

    if 'Showers' in forecast or 'Rain' in forecast or 'Thunderstorm' in forecast:
        idx = random.randint(0, len(rain_comments))
        msg_output = msg_output + "\n" + rain_comments[idx]

    return msg_output


def pollPM25(region):
    pm25_one_hourly = 'invalid'
    url = DATAGOV_URI + "environment/pm25"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output, pm25_one_hourly
    region_list = ['west', 'east', 'central', 'south', 'north']
    if region in region_list:
        time_stamp_str = req.json()['items'][0]['timestamp']
        time_stamp_idx = time_stamp_str.find('T')
        time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
        pm25_one_hourly = req.json()['items'][0]['readings']['pm25_one_hourly'][region]
        pm25_one_hourly = int(pm25_one_hourly)
        if pm25_one_hourly < 55:
            pm25_rating = "Normal"
        elif pm25_one_hourly < 150:
            pm25_rating = "Elevated"
        elif pm25_one_hourly < 250:
            pm25_rating = "`High`"
        else:
            pm25_rating = "`Very High`"
        output = "*%s* PM25 (1Hr) (_%s_): %d (%s)" % (region, time_stamp, pm25_one_hourly, pm25_rating)
    else:
        output = "Region *%s* not found. Please enter one of the following valid regions:\n" % region
        first = True
        for i in range(len(region_list)):
            if first:
                first = False
                output = output + region_list[i]
            else:
                output = output + ", " + region_list[i]
    return output, pm25_one_hourly


def pollTemp():
    temp = 'invalid'
    url = DATAGOV_URI + "environment/air-temperature"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output, temp
    time_stamp_str = req.json()['items'][0]['timestamp']
    time_stamp_idx = time_stamp_str.find('T')
    time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
    temp = req.json()['items'][0]['readings'][0]['value']
    output = "Temperature (_%s_): %sdegC" % (time_stamp, temp)
    return output, temp


def pollPSI(region):
    url = DATAGOV_URI + "environment/psi"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output
    region_list = ['west', 'national', 'east', 'central', 'south', 'north']
    if region in region_list:
        time_stamp_str = req.json()['items'][0]['timestamp']
        time_stamp_idx = time_stamp_str.find('T')
        time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
        o3_sub_index = req.json()['items'][0]['readings']['o3_sub_index'][region]
        pm10_twenty_four_hourly = req.json()['items'][0]['readings']['pm10_twenty_four_hourly'][region]
        pm10_sub_index = req.json()['items'][0]['readings']['pm10_sub_index'][region]
        co_sub_index = req.json()['items'][0]['readings']['co_sub_index'][region]
        pm25_twenty_four_hourly = req.json()['items'][0]['readings']['pm25_twenty_four_hourly'][region]
        pm25_twenty_four_hourly = int(pm25_twenty_four_hourly)
        if pm25_twenty_four_hourly < 55:
            pm25_rating = "Normal"
        elif pm25_twenty_four_hourly < 150:
            pm25_rating = "Elevated"
        elif pm25_twenty_four_hourly < 250:
            pm25_rating = "`High`"
        else:
            pm25_rating = "`Very High`"
        so2_sub_index = req.json()['items'][0]['readings']['so2_sub_index'][region]
        co_eight_hour_max = req.json()['items'][0]['readings']['co_eight_hour_max'][region]
        no2_one_hour_max = req.json()['items'][0]['readings']['no2_one_hour_max'][region]
        so2_twenty_four_hourly = req.json()['items'][0]['readings']['so2_twenty_four_hourly'][region]
        pm25_sub_index = req.json()['items'][0]['readings']['pm25_sub_index'][region]
        psi_twenty_four_hourly = req.json()['items'][0]['readings']['psi_twenty_four_hourly'][region]
        psi_twenty_four_hourly = int(psi_twenty_four_hourly)
        if psi_twenty_four_hourly < 50:
            psi_24hr_rating = "Good"
        elif psi_twenty_four_hourly < 100:
            psi_24hr_rating = "Moderate"
        elif psi_twenty_four_hourly < 200:
            psi_24hr_rating = "`Unhealthy`"
        elif psi_twenty_four_hourly < 300:
            psi_24hr_rating = "`Very Unhealthy`"
        else:
            psi_24hr_rating = "`Hazardous`"
        o3_eight_hour_max = req.json()['items'][0]['readings']['o3_eight_hour_max'][region]
        output = "*%s*\n" % region + \
                 "O3 Sub: %s\n" % o3_sub_index + \
                 "PM10 (24Hr): %s\n" % pm10_twenty_four_hourly + \
                 "PM10 Sub: %s\n" % pm10_sub_index + \
                 "CO Sub: %s\n" % co_sub_index + \
                 "PM25 (24Hr): %d (%s)\n" % (pm25_twenty_four_hourly, pm25_rating) + \
                 "SO2 Sub: %s\n" % so2_sub_index + \
                 "CO (8Hr): %s\n" % co_eight_hour_max + \
                 "NO2 (1Hr Max): %s\n" % no2_one_hour_max + \
                 "SO2 (24Hr): %s\n" % so2_twenty_four_hourly + \
                 "PM25 Sub: %s\n" % pm25_sub_index + \
                 "PSI (24Hr): %d (%s)\n" % (psi_twenty_four_hourly, psi_24hr_rating) + \
                 "O3 (8Hr Max): %s" % o3_eight_hour_max
    else:
        output = "Region *%s* not found. Please enter one of the following valid regions:\n" % region
        first = True
        for i in range(len(region_list)):
            if first:
                first = False
                output = output + region_list[i]
            else:
                output = output + ", " + region_list[i]
    return output


def poll24HrForecast(region):
    url = DATAGOV_URI + "environment/24-hour-weather-forecast"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output
    region_list = ['west', 'east', 'central', 'south', 'north']
    if region in region_list:
        # Period 1: 6am - 12pm today
        forecast1 = req.json()['items'][0]['periods'][0]['regions'][region]
        # Period 2: 12pm to 6pm today
        forecast2 = req.json()['items'][0]['periods'][1]['regions'][region]
        # Period 3: 6pm today to 6am tmr
        forecast3 = req.json()['items'][0]['periods'][2]['regions'][region]
        output = "*%s* 24Hr Forecast\n" % region + \
                 "6am to 12pm: %s\n" % forecast1 + \
                 "12pm to 6pm: %s\n" % forecast2 + \
                 "6pm to 6am tomorrow: %s" % forecast3
        return output
    else:  # display general info if no region specified
        start_period = req.json()['items'][0]['valid_period']['start']
        start_period_idx = start_period.find('T')
        start_time = start_period[start_period_idx + 1:start_period_idx + 6]
        end_period = req.json()['items'][0]['valid_period']['end']
        end_period_idx = end_period.find('T')
        end_time = end_period[end_period_idx + 1:end_period_idx + 6]
        forecast = req.json()['items'][0]['general']['forecast']
        humidity_low = req.json()['items'][0]['general']['relative_humidity']['low']
        humidity_high = req.json()['items'][0]['general']['relative_humidity']['high']
        temp_low = req.json()['items'][0]['general']['temperature']['low']
        temp_high = req.json()['items'][0]['general']['temperature']['high']
        wind_low = req.json()['items'][0]['general']['wind']['speed']['low']
        wind_high = req.json()['items'][0]['general']['wind']['speed']['high']
        wind_dir = req.json()['items'][0]['general']['wind']['direction']
        output = "*Singapore* 24Hr Forecast (6am to 6am tomorrow)\n" + \
                 "Forecast: %s\n" % forecast + \
                 "Humidity: %s to %s%%\n" % (humidity_low, humidity_high) + \
                 "Temperature: %s to %sdegC\n" % (temp_low, temp_high) + \
                 "Wind: %s to %s, %s" % (wind_low, wind_high, wind_dir)
        return output


def poll4dayForecast():
    url = DATAGOV_URI + "environment/4-day-weather-forecast"
    req = requests.get(url, headers=data_gov_headers)
    if isAPIhealthy(req) is False:
        output = "API is down!"
        return output
    output = "*Singapore* 4 Day Forecast\n"
    for i in range(4):
        date = req.json()['items'][0]['forecasts'][i]['date']
        forecast = req.json()['items'][0]['forecasts'][i]['forecast']
        humidity_low = req.json()['items'][0]['forecasts'][i]['relative_humidity']['low']
        humidity_high = req.json()['items'][0]['forecasts'][i]['relative_humidity']['high']
        temp_low = req.json()['items'][0]['forecasts'][i]['temperature']['low']
        temp_high = req.json()['items'][0]['forecasts'][i]['temperature']['high']
        wind_low = req.json()['items'][0]['forecasts'][i]['wind']['speed']['low']
        wind_high = req.json()['items'][0]['forecasts'][i]['wind']['speed']['high']
        wind_dir = req.json()['items'][0]['forecasts'][i]['wind']['direction']
        output = output + "_%s_\n" % date + \
                 "Forecast: %s\n" % forecast + \
                 "Humidity: %s to %s%%\n" % (humidity_low, humidity_high) + \
                 "Temperature: %s to %sdegC\n" % (temp_low, temp_high) + \
                 "Wind: %s to %s, %s\n" % (wind_low, wind_high, wind_dir)
    return output


def isBusStopValid(stop_code):
    url = LTADATAMALL_URI + "BusArrivalv2?BusStopCode=%s" % stop_code
    req = requests.get(url, headers=ltadatamall_headers)
    services = req.json()['Services']
    return isList(services)


def pollBusStop(stop_code):
    url = LTADATAMALL_URI + "BusArrivalv2?BusStopCode=%s" % stop_code
    req = requests.get(url, headers=ltadatamall_headers)
    services = req.json()['Services']
    output = "*Bus Stop %s*\n" % (stop_code)
    # check cache for bus stop description
    stops = json.loads(open(LTADATAMALL_STOPS_JSON_PATH).read())
    stop_code_map = {stop["BusStopCode"]: stop for stop in stops}
    output = output + stop_code_map[str(stop_code)]["Description"] + "\n"
    # check valid stop code
    if isList(services) is False:
        output = output + "`Invalid stop code!`"
        return output
    for service in services:
        # next bus 1
        str_est_arrive_time = service['NextBus']['EstimatedArrival']
        if str_est_arrive_time == '':
            output = output + service['ServiceNo'] + ":\n"
            continue
        est_arrive_time = datetime.datetime.strptime(str_est_arrive_time, '%Y-%m-%dT%H:%M:%S+08:00')
        now_time = datetime.datetime.now()
        if est_arrive_time > now_time:
            time_diff = est_arrive_time - now_time
            time_diff_min = time_diff.seconds / 60
        else:
            time_diff_min = 0
        if time_diff_min < 1:
            time_diff_str = "*Arr*"
        else:
            time_diff_str = "%dmin" % (round(time_diff_min))
        load = service['NextBus']['Load']
        if load == 'LSD':  # Limited Standing
            output = output + service['ServiceNo'] + ": %s (%s) (`Full`)" % (
                time_diff_str, est_arrive_time.strftime("%H:%M"))
        else:
            output = output + service['ServiceNo'] + ": %s (%s)" % (
                time_diff_str, est_arrive_time.strftime("%H:%M"))
        # next bus 2
        str_est_arrive_time = service['NextBus2']['EstimatedArrival']
        if str_est_arrive_time == '':
            output = output + "\n"
            continue
        est_arrive_time = datetime.datetime.strptime(str_est_arrive_time, '%Y-%m-%dT%H:%M:%S+08:00')
        time_diff = est_arrive_time - now_time
        time_diff_str = "%dmin" % (round(time_diff.seconds / 60))
        load = service['NextBus']['Load']
        if load == 'LSD':  # Limited Standing
            output = output + " | %s (`Full`)" % (time_diff_str)
        else:
            output = output + " | %s" % (time_diff_str)
        # next bus 3
        str_est_arrive_time = service['NextBus3']['EstimatedArrival']
        if str_est_arrive_time == '':
            output = output + "\n"
            continue
        est_arrive_time = datetime.datetime.strptime(str_est_arrive_time, '%Y-%m-%dT%H:%M:%S+08:00')
        time_diff = est_arrive_time - now_time
        time_diff_str = "%dmin" % (round(time_diff.seconds / 60))
        output = output + " | %s\n" % (time_diff_str)
    return output


def pollNextBus(stop_code, bus_num, arrival_min):
    ret = -3  # alert bus num not found at bus stop
    output = ""
    url = LTADATAMALL_URI + "BusArrivalv2?BusStopCode=%s" % stop_code
    req = requests.get(url, headers=ltadatamall_headers)
    services = req.json()['Services']
    for service in services:
        # check against requested bus no
        if str(bus_num) != service['ServiceNo']:
            continue
        # check bus arriving
        str_est_arrive_time = service['NextBus']['EstimatedArrival']
        if str_est_arrive_time == '':
            ret = -1  # alert no bus
            return ret, output
        est_arrive_time = datetime.datetime.strptime(str_est_arrive_time, '%Y-%m-%dT%H:%M:%S+08:00')
        now_time = datetime.datetime.now()
        if est_arrive_time > now_time:
            time_diff = est_arrive_time - now_time
            time_diff_min = time_diff.seconds / 60
        else:
            time_diff_min = 0
        if time_diff_min <= 1:
            ret = 1  # alert bus arriving in 1min
            time_diff_str = "Arr"
        elif time_diff_min <= arrival_min:
            ret = 2  # alert bus arriving in specified min
            time_diff_str = "%dmin" % (round(time_diff_min))
        else:
            ret = 0  # no alert
            time_diff_str = "%dmin" % (round(time_diff_min))
        load = service['NextBus']['Load']
        if load == 'LSD':  # Limited Standing
            ret = -2  # alert next bus full
            output = "Next Bus %s: *%s* (%s) (`Full`)" % (
                service['ServiceNo'], time_diff_str, est_arrive_time.strftime("%H:%M"))
        else:
            output = "Next Bus %s: *%s* (%s)" % (
                service['ServiceNo'], time_diff_str, est_arrive_time.strftime("%H:%M"))
        break
    return ret, output


def pollTrainServiceAlerts(title_msg):
    global prev_train_msg_text

    url = LTADATAMALL_URI + "TrainServiceAlerts"
    req = requests.get(url, headers=ltadatamall_headers)
    if req:
        status = int(req.json()['value']['Status'])
        msg = req.json()['value']['Message']
    else:
        status = 0
        msg = False
    output = title_msg

    # disruption status
    isDisrupted = False
    if status == 1:
        output = output + "```A Normal Train Service```"
    elif status == 2:
        output = output + "```A Disrupted Train Service```"
        isDisrupted = True
    else:
        output = "`API Error!`"

    # alert msg
    validMsg = False
    if msg:
        validMsg = True
        msg_text = msg[0]['Content']
        msg_text_tmp = msg_text.lower()
        if msg_text_tmp.find('fault') != 0:
            isDisrupted = True
        output = output + "\n" + msg_text

    return isDisrupted, validMsg, output


class SGdataBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(SGdataBot, self).__init__(*args, **kwargs)
        self.state = 'inactive'
        self.state_param = 0
        self.last_msg_id = 0

    def on_chat_message(self, msg):
        # check and only respond to text messages
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text' or content_type == 'location':
            self.chat_handle(msg, content_type)

    def on_callback_query(self, msg):
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        self.query_handle(msg, query_id, chat_id, query_data)

    def checkInputEmpty(self, chat_id, input):
        if input == '':  # empty input
            # output = "This command requires an input."
            # bot.sendMessage(chat_id, output)
            return True

        return False

    # Bot query callback handler
    def query_handle(self, msg, query_id, chat_id, query_data):
        try:
            chat_name = msg['from']['username']
        except:
            chat_name = "noname"

        if query_data == "refresh":
            user_loc = self.state_param
            stops = json.loads(open(LTADATAMALL_STOPS_JSON_PATH).read())
            output = ""
            for stop in stops:
                stop_loc = (stop['Latitude'], stop['Longitude'])
                dist = geopy.distance.distance(user_loc, stop_loc).km
                if dist <= (BUSSTOP_SEARCH_DIST / 1000.0):
                    output = output + stop['Description'] + " "
                    output = output + pollBusStop(stop['BusStopCode'])
                    output = output + "https://www.google.com.sg/maps/place/%s,%s\n" % (stop_loc[0], stop_loc[1])
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text='Refresh', callback_data='refresh')]])
            bot.editMessageText((chat_id, self.last_msg_id), text=output, reply_markup=reply_markup,
                                parse_mode='Markdown', \
                                disable_web_page_preview=True)
        return

    # Bot chat handler
    def chat_handle(self, msg, content_type):
        chat_id = msg['chat']['id']
        if content_type == 'text':
            msg_text = msg['text']
        elif content_type == 'location':
            msg_location = msg['location']
        chat_type = msg['chat']['type']
        if chat_type == 'private':
            try:
                chat_name = msg['chat']['username']
            except:
                chat_name = "noname"
        elif chat_type == 'group' or chat_type == 'supergroup' or chat_type == 'channel':
            chat_name = msg['chat']['title']
        else:
            chat_name = "noname"

        # Check msg
        if content_type == 'text':
            if msg_text[0] == '/':  # text is a command
                bot_name_index = msg_text.find(BOT_NAME)
                if bot_name_index != -1:  # command with @BOT_NAME
                    command = msg_text[0:bot_name_index]
                    input = msg_text[bot_name_index + len(BOT_NAME) + 1:]
                else:  # plain command
                    first_space_index = msg_text.find(' ')
                    if first_space_index != -1:  # input after command
                        command = msg_text[0:first_space_index]
                        input = msg_text[first_space_index + 1:]
                    else:  # command only
                        command = msg_text
                        input = ''
            else:  # text is a reply
                command = ''
                input = msg_text
        elif content_type == 'location':
            command = ''
            input = msg_location

        # Received msg printout
        curr_time = datetime.datetime.now()
        print ("[%s] <%s %s> sent command '%s', input '%s'" \
               % (curr_time.strftime("%x, %X"), chat_name, chat_id, command, input))

        # Check for special states
        if self.state == 'forecastnearme reply':
            self.state = 'inactive'
            min_dist = 0
            min_dist_station = 'none'
            user_loc = (msg_location['latitude'], msg_location['longitude'])
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            url = DATAGOV_URI + "environment/2-hour-weather-forecast"
            req = requests.get(url, headers=data_gov_headers)
            if isAPIhealthy(req) is False:
                output = "API is down!"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                return
            for i in req.json()['area_metadata']:
                station_loc = (i['label_location']['latitude'], i['label_location']['longitude'])
                dist = geopy.distance.distance(user_loc, station_loc).km
                if min_dist == 0 or dist < min_dist:
                    min_dist = dist
                    min_dist_station = i['name']
                    output = "You are closest (_%.2fkm_) to *%s*.\n" % (min_dist, min_dist_station)
                    for i in req.json()['items'][0]['forecasts']:
                        if i['area'] == min_dist_station:
                            start_period = req.json()['items'][0]['valid_period']['start']
                            start_period_idx = start_period.find('T')
                            start_time = start_period[start_period_idx + 1:start_period_idx + 6]
                            end_period = req.json()['items'][0]['valid_period']['end']
                            end_period_idx = end_period.find('T')
                            end_time = end_period[end_period_idx + 1:end_period_idx + 6]
                            forecast = i['forecast']
                            output = output + "2Hr Forecast (%s - %s):\n```%s```" % (start_time, end_time, forecast)
                            break
            if 'Showers' in forecast or 'Rain' in forecast or 'Thunderstorm' in forecast:
                idx = random.randint(0, len(rain_comments))
                output = output + "\n\n" + rain_comments[idx]
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        elif self.state == 'pm25 reply':
            self.state = 'inactive'
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            output = "Smelling the air..."
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            output, pm25_one_hourly = pollPM25(input)
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif self.state == 'pm25nearme reply':
            self.state = 'inactive'
            min_dist = 0
            min_dist_station = 'none'
            user_loc = (msg_location['latitude'], msg_location['longitude'])
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            url = DATAGOV_URI + "environment/pm25"
            req = requests.get(url, headers=data_gov_headers)
            if isAPIhealthy(req) is False:
                output = "API is down!"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                return
            for i in req.json()['region_metadata']:
                station_loc = (i['label_location']['latitude'], i['label_location']['longitude'])
                dist = geopy.distance.distance(user_loc, station_loc).km
                if min_dist == 0 or dist < min_dist:
                    min_dist = dist
                    min_dist_station = i['name']
                    output = "You are closest (_%.2fkm_) to *%s*.\n" % (min_dist, min_dist_station)
                    time_stamp_str = req.json()['items'][0]['timestamp']
                    time_stamp_idx = time_stamp_str.find('T')
                    time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
                    pm25_one_hourly = req.json()['items'][0]['readings']['pm25_one_hourly'][min_dist_station]
                    pm25_one_hourly = int(pm25_one_hourly)
                    if pm25_one_hourly < 55:
                        pm25_rating = "Normal"
                    elif pm25_one_hourly < 150:
                        pm25_rating = "Elevated"
                    elif pm25_one_hourly < 250:
                        pm25_rating = "`High`"
                    else:
                        pm25_rating = "`Very High`"
                    output = output + "PM25 (1Hr) (%s): %d (%s)" % (time_stamp, pm25_one_hourly, pm25_rating)
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        elif self.state == 'psi reply':
            self.state = 'inactive'
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            output = "Smelling the air..."
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            output = pollPSI(input)
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif self.state == 'psinearme reply':
            self.state = 'inactive'
            min_dist = 0
            min_dist_station = 'none'
            user_loc = (msg_location['latitude'], msg_location['longitude'])
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            url = DATAGOV_URI + "environment/psi"
            req = requests.get(url, headers=data_gov_headers)
            if isAPIhealthy(req) is False:
                output = "API is down!"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                return
            for i in req.json()['region_metadata']:
                station_loc = (i['label_location']['latitude'], i['label_location']['longitude'])
                dist = geopy.distance.distance(user_loc, station_loc).km
                if min_dist == 0 or dist < min_dist:
                    min_dist = dist
                    min_dist_station = i['name']
                    output = "You are closest (_%.2fkm_) to *%s*.\n" % (min_dist, min_dist_station)
                    time_stamp_str = req.json()['items'][0]['timestamp']
                    time_stamp_idx = time_stamp_str.find('T')
                    time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
                    o3_sub_index = req.json()['items'][0]['readings']['o3_sub_index'][min_dist_station]
                    pm10_twenty_four_hourly = req.json()['items'][0]['readings']['pm10_twenty_four_hourly'][
                        min_dist_station]
                    pm10_sub_index = req.json()['items'][0]['readings']['pm10_sub_index'][min_dist_station]
                    co_sub_index = req.json()['items'][0]['readings']['co_sub_index'][min_dist_station]
                    pm25_twenty_four_hourly = req.json()['items'][0]['readings']['pm25_twenty_four_hourly'][
                        min_dist_station]
                    pm25_twenty_four_hourly = int(pm25_twenty_four_hourly)
                    if pm25_twenty_four_hourly < 55:
                        pm25_rating = "Normal"
                    elif pm25_twenty_four_hourly < 150:
                        pm25_rating = "Elevated"
                    elif pm25_twenty_four_hourly < 250:
                        pm25_rating = "`High`"
                    else:
                        pm25_rating = "`Very High`"
                    so2_sub_index = req.json()['items'][0]['readings']['so2_sub_index'][min_dist_station]
                    co_eight_hour_max = req.json()['items'][0]['readings']['co_eight_hour_max'][min_dist_station]
                    no2_one_hour_max = req.json()['items'][0]['readings']['no2_one_hour_max'][min_dist_station]
                    so2_twenty_four_hourly = req.json()['items'][0]['readings']['so2_twenty_four_hourly'][
                        min_dist_station]
                    pm25_sub_index = req.json()['items'][0]['readings']['pm25_sub_index'][min_dist_station]
                    psi_twenty_four_hourly = req.json()['items'][0]['readings']['psi_twenty_four_hourly'][
                        min_dist_station]
                    psi_twenty_four_hourly = int(psi_twenty_four_hourly)
                    if psi_twenty_four_hourly < 50:
                        psi_24hr_rating = "Good"
                    elif psi_twenty_four_hourly < 100:
                        psi_24hr_rating = "Moderate"
                    elif psi_twenty_four_hourly < 200:
                        psi_24hr_rating = "`Unhealthy`"
                    elif psi_twenty_four_hourly < 300:
                        psi_24hr_rating = "`Very Unhealthy`"
                    else:
                        psi_24hr_rating = "`Hazardous`"
                    o3_eight_hour_max = req.json()['items'][0]['readings']['o3_eight_hour_max'][min_dist_station]
                    output = output + "*%s* (_%s_)\n" % (min_dist_station, time_stamp) + \
                             "O3 Sub: %s\n" % o3_sub_index + \
                             "PM10 (24Hr): %s\n" % pm10_twenty_four_hourly + \
                             "PM10 Sub: %s\n" % pm10_sub_index + \
                             "CO Sub: %s\n" % co_sub_index + \
                             "PM25 (24Hr): %d (%s)\n" % (pm25_twenty_four_hourly, pm25_rating) + \
                             "SO2 Sub: %s\n" % so2_sub_index + \
                             "CO (8Hr): %s\n" % co_eight_hour_max + \
                             "NO2 (1Hr Max): %s\n" % no2_one_hour_max + \
                             "SO2 (24Hr): %s\n" % so2_twenty_four_hourly + \
                             "PM25 Sub: %s\n" % pm25_sub_index + \
                             "PSI (24Hr): %d (%s)\n" % (psi_twenty_four_hourly, psi_24hr_rating) + \
                             "O3 (8Hr Max): %s" % o3_eight_hour_max
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        elif self.state == 'traffic reply 1':
            self.state = 'traffic reply 2'
            self.state_param = (msg_location['latitude'], msg_location['longitude'])
            location_keyboard = [[KeyboardButton(text="500m away")],
                                 [KeyboardButton(text="1km away")],
                                 [KeyboardButton(text="1.5km away")]]
            reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "See how far away?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        elif self.state == 'traffic reply 2':
            self.state = 'inactive'
            idx = input.find('km')
            if idx != -1:  # kilometers
                desired_dist = float(input[0:idx])
            else:  # meters
                idx = input.find('m')
                desired_dist = float(input[0:idx]) / 1000.0
            user_loc = self.state_param
            self.state_param = (0, 0)
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            url = DATAGOV_URI + "transport/traffic-images"
            req = requests.get(url, headers=data_gov_headers)
            if isAPIhealthy(req) is False:
                output = "API is down!"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                return
            output = "I saw traffic at the following roads _%skm_ away from you...\n" % desired_dist
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            for i in req.json()['items'][0]['cameras']:
                cam_loc = (i['location']['latitude'], i['location']['longitude'])
                dist = geopy.distance.distance(user_loc, cam_loc).km
                if dist <= desired_dist:
                    time_stamp_str = i['timestamp']
                    time_stamp_idx = time_stamp_str.find('T')
                    time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
                    cam_id = i['camera_id']
                    caption = "Cam ID %s (%s) at %.2fkm away" % (cam_id, time_stamp, dist)
                    photo_url = i['image']
                    bot.sendPhoto(chat_id, photo_url, caption=caption)
            output = "I see see look look until no more liao."
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif self.state == 'carpark reply 1':
            self.state = 'carpark reply 2'
            self.state_param = (msg_location['latitude'], msg_location['longitude'])
            location_keyboard = [[KeyboardButton(text="100m away")],
                                 [KeyboardButton(text="200m away")],
                                 [KeyboardButton(text="300m away")]]
            reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "Check how far away?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        elif self.state == 'carpark reply 2':
            self.state = 'inactive'
            idx = input.find('km')
            if idx != -1:  # kilometers
                desired_dist = float(input[0:idx])
            else:  # meters
                idx = input.find('m')
                desired_dist = float(input[0:idx]) / 1000.0
            user_loc = self.state_param
            self.state_param = (0, 0)
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            url = DATAGOV_URI + "transport/carpark-availability"
            req = requests.get(url, headers=data_gov_headers)
            # carpark API no health status
            # if isAPIhealthy(req) is False:
            #        output = "API is down!"
            #        bot.sendMessage(chat_id, output, reply_markup=reply_markup)
            #        return
            output = "I found parking at the following carparks _%skm_ away from you...\n" % desired_dist
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            cv = SVY21()  # init mod to convert carpark SVY21 coords to lat/lon
            for i in req.json()['items'][0]['carpark_data']:
                carpark_num = i['carpark_number']
                with open(HDB_CARPARK_CSV_PATH, 'rt') as f:  # open ref csv to match carpark num to lat/lon
                    reader = csv.reader(f, delimiter=',')
                    for row in reader:
                        if carpark_num == row[0]:  # check carpark num match
                            carpark_loc = cv.computeLatLon(float(row[3]), float(row[2]))  # get carpark lat/lon
                            dist = geopy.distance.distance(user_loc, carpark_loc).km
                            if dist <= desired_dist:
                                # push carpark info out
                                carpark_addr = row[1]
                                total_lots = i['carpark_info'][0]['total_lots']
                                lots_available = i['carpark_info'][0]['lots_available']
                                output = "*Carpark %s*, _%.2fkm_ away\n" % (carpark_num, dist) + \
                                         "%s\n" % (carpark_addr) + \
                                         "Available Lots: *%s* of %s\n" % (lots_available, total_lots) + \
                                         "Free Parking: %s\n" % (row[7]) + \
                                         "https://www.google.com.sg/maps/place/%s,%s" % (carpark_loc[0], carpark_loc[1])
                                bot.sendMessage(chat_id, output, parse_mode='Markdown', disable_web_page_preview=True)
                            break
            output = "I find until no more liao."
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif self.state == 'busstop reply':
            self.state = 'inactive'
            self.state_param = (msg_location['latitude'], msg_location['longitude'])
            user_loc = self.state_param
            stops = json.loads(open(LTADATAMALL_STOPS_JSON_PATH).read())
            output = "Bus Stops _%sm_ away from you:\n" % (BUSSTOP_SEARCH_DIST)
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            output = ""
            noMatch = True
            for stop in stops:
                stop_loc = (stop['Latitude'], stop['Longitude'])
                dist = geopy.distance.distance(user_loc, stop_loc).km
                if dist <= (BUSSTOP_SEARCH_DIST / 1000.0):
                    noMatch = False
                    output = output + stop['Description'] + " "
                    output = output + pollBusStop(stop['BusStopCode'])
                    output = output + "https://www.google.com.sg/maps/place/%s,%s\n" % (stop_loc[0], stop_loc[1])
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text='Refresh', callback_data='refresh')]])
            if noMatch is True:
                output = "Your there too ulu got no bus stop within _%sm_!" % (BUSSTOP_SEARCH_DIST)
                reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            Message = bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown',
                                      disable_web_page_preview=True)
            self.last_msg_id = Message['message_id']
            return

        # Command processing
        if command == '/forecast':
            if self.checkInputEmpty(chat_id, input) is True:
                output = "Please select enter a valid area (E.g. /forecast Ang Mo Kio)."
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
                return
            output = "Asking Sky..."
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            output, forecast, end_time = poll2hrForecast(input)
            if 'Showers' in forecast or 'Rain' in forecast or 'Thunderstorm' in forecast:
                idx = random.randint(0, len(rain_comments))
                output = output + "\n" + rain_comments[idx]
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/forecastnearme':
            location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "You where now arh?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            self.state = 'forecastnearme reply'
            return
        elif command == '/forecastupdate':
            msg_output = forcedRainUpdate(chat_id)
            bot.sendMessage(chat_id, msg_output, parse_mode='Markdown')
            return
        elif command == '/rainalertadd':
            if self.checkInputEmpty(chat_id, input) is True:
                return
            output = "Adding area..."
            bot.sendMessage(chat_id, output)
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table_name = str(chat_id) + "_arealist"
            table = db[table_name]
            alert_area = input
            if is2hrForecastAreaValid(alert_area) is True:  # check for valid area
                if table.find_one(area=alert_area) is None:
                    table.insert(dict(area=alert_area, prev_forecast="none"))
                    output = "*%s* is added to your rain alert." % (alert_area)
                else:
                    output = "*%s* is already on your rain alert." % (alert_area)
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Area *%s* not found. Please select enter one of the following valid areas:\n" % (alert_area)
                area_list = ""
                first = True
                url = DATAGOV_URI + "environment/2-hour-weather-forecast"
                req = requests.get(url, headers=data_gov_headers)
                if isAPIhealthy(req) is False:
                    output = "API is down!"
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                for i in req.json()['items'][0]['forecasts']:
                    if first:
                        first = False
                        area_list = area_list + i['area']
                    else:
                        area_list = area_list + ", " + i['area']
                output = output + area_list
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/rainalertdelete':
            if self.checkInputEmpty(chat_id, input) is True:
                return
            output = "Deleting area..."
            bot.sendMessage(chat_id, output)
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table_name = str(chat_id) + "_arealist"
            table = db[table_name]
            alert_area = input
            if is2hrForecastAreaValid(alert_area) is True:  # check for valid area
                if table.find_one(area=alert_area) is not None:
                    table.delete(area=alert_area)
                    output = "*%s* has been deleted from your rain alert." % (alert_area)
                else:
                    output = "*%s* was not on your rain alert in the first place!" % (alert_area)
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Area *%s* not found. Please select enter one of the following valid areas:\n" % (alert_area)
                area_list = ""
                first = True
                url = DATAGOV_URI + "environment/2-hour-weather-forecast"
                req = requests.get(url, headers=data_gov_headers)
                if isAPIhealthy(req) is False:
                    output = "API is down!"
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                for i in req.json()['items'][0]['forecasts']:
                    if first:
                        first = False
                        area_list = area_list + i['area']
                    else:
                        area_list = area_list + ", " + i['area']
                output = output + area_list
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/rainalertlist':
            output = "Checking list..."
            bot.sendMessage(chat_id, output)
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table_name = str(chat_id) + "_arealist"
            table = db[table_name]
            output = "`Active Alerts`\n"
            for alerts in table:
                output = output + alerts['area'] + "\n"
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/subscriberainalert':
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table = db['rain_alert']
            if table.find_one(chatid=chat_id) is None:  # NOT registered yet
                table.insert(dict(chatid=chat_id))
                output = "You are now subscribed to rain alerts."
                bot.sendMessage(chat_id, output)
            else:
                output = "You are already subscribed to rain alerts!"
                bot.sendMessage(chat_id, output)
            return
        elif command == '/unsubscriberainalert':
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table = db['rain_alert']
            if table.find_one(chatid=chat_id) is not None:  # registered
                table.delete(chatid=chat_id)
                output = "You are now unsubscribed from rain alerts."
                bot.sendMessage(chat_id, output)
            else:
                output = "You are not subscribed to rain alerts in the first place!"
                bot.sendMessage(chat_id, output)
            return
        elif command == '/pm25':
            region_keyboard = [[KeyboardButton(text='west'), KeyboardButton(text='east')],
                               [KeyboardButton(text='south'), KeyboardButton(text='north')],
                               [KeyboardButton(text='central')]]
            reply_markup = ReplyKeyboardMarkup(keyboard=region_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "Where air dirty arh?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            self.state = 'pm25 reply'
        elif command == '/pm25nearme':
            location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "You where now arh?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            self.state = 'pm25nearme reply'
        elif command == '/temp':
            output = "Finding my thermometer..."
            bot.sendMessage(chat_id, output)
            output, temp = pollTemp()
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/psi':
            region_keyboard = [[KeyboardButton(text='west'), KeyboardButton(text='east')],
                               [KeyboardButton(text='south'), KeyboardButton(text='north')],
                               [KeyboardButton(text='central'), KeyboardButton(text='national')]]
            reply_markup = ReplyKeyboardMarkup(keyboard=region_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "Where air dirty arh?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            self.state = 'psi reply'
        elif command == '/psinearme':
            location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            output = "You where now arh?"
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            self.state = 'psinearme reply'
        elif command == '/forecast24h':
            if self.checkInputEmpty(chat_id, input) is True:
                input = 'none'
            output = "Asking Sky..."
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            output = poll24HrForecast(input)
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/forecast4day':
            output = "Asking Sky..."
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            output = poll4dayForecast()
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/traffic':
            if self.checkInputEmpty(chat_id, input) is True:
                location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
                reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True,
                                                   one_time_keyboard=True)
                output = "You where now arh?"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                self.state = 'traffic reply 1'
            else:
                url = DATAGOV_URI + "transport/traffic-images"
                req = requests.get(url, headers=data_gov_headers)
                if isAPIhealthy(req) is False:
                    output = "API is down!"
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                output = "Spying traffic at *Cam ID %s*...\n" % input
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
                for i in req.json()['items'][0]['cameras']:
                    if i['camera_id'] == input:
                        time_stamp_str = i['timestamp']
                        time_stamp_idx = time_stamp_str.find('T')
                        time_stamp = time_stamp_str[time_stamp_idx + 1:time_stamp_idx + 6]
                        cam_loc = (i['location']['latitude'], i['location']['longitude'])
                        caption = "Cam ID %s (%s) at %s" % (input, time_stamp, cam_loc)
                        photo_url = i['image']
                        bot.sendPhoto(chat_id, photo_url, caption=caption)
                        return
                # if reach this point, cam id not found
                output = "Cam ID %s not found!" % input
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/carpark':
            if self.checkInputEmpty(chat_id, input) is True:
                location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
                reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True,
                                                   one_time_keyboard=True)
                output = "You where now arh?"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                self.state = 'carpark reply 1'
            else:
                url = DATAGOV_URI + "transport/carpark-availability"
                req = requests.get(url, headers=data_gov_headers)
                geolocator = Nominatim()
                location = geolocator.geocode(input)
                if str(location) == 'None':  # unable to geocode user-input addr
                    output = "Cannot find *%s* leh!" % input
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                output = "Finding parking near *%s*...\n" % location.address
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
                user_loc = (location.latitude, location.longitude)
                min_dist = 0
                cv = SVY21()  # init mod to convert carpark SVY21 coords to lat/lon
                for i in req.json()['items'][0]['carpark_data']:
                    carpark_num = i['carpark_number']
                    with open(HDB_CARPARK_CSV_PATH, 'rt') as f:  # open ref csv to match carpark num to lat/lon
                        reader = csv.reader(f, delimiter=',')
                        for row in reader:
                            if carpark_num == row[0]:  # check carpark num match
                                carpark_loc = cv.computeLatLon(float(row[3]), float(row[2]))  # get carpark lat/lon
                                dist = geopy.distance.distance(user_loc, carpark_loc).km
                                if min_dist == 0 or dist <= min_dist:
                                    min_dist = dist
                                    carpark_addr = row[1]
                                    total_lots = i['carpark_info'][0]['total_lots']
                                    lots_available = i['carpark_info'][0]['lots_available']
                                    output = "Nearest carpark %s, _%.2fkm_ away\n" % (carpark_num, dist) + \
                                             "%s\n" % (carpark_addr) + \
                                             "Available Lots: *%s* of %s\n" % (lots_available, total_lots) + \
                                             "https://www.google.com.sg/maps/place/%s,%s" % (
                                             carpark_loc[0], carpark_loc[1])
                                break
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
                return
        elif command == '/busstop':
            if self.checkInputEmpty(chat_id, input) is True:
                location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
                reply_markup = ReplyKeyboardMarkup(keyboard=location_keyboard, resize_keyboard=True,
                                                   one_time_keyboard=True)
                output = "You where now arh?"
                bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
                self.state = 'busstop reply'
            else:
                output = pollBusStop(input)
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busarrive':
            if self.checkInputEmpty(chat_id, input) is False:
                # process bus stop number and bus service number
                idx = input.find(' ')
                stop_code = int(input[0:idx])
                bus_num = input[idx + 1:]
                bus_num = bus_num.upper()
                status, output = pollNextBus(stop_code, bus_num, 1)
                if status == 1:  # bus already arriving so alert immediately
                    output = "Bus *%s* is `arriving now` at Bus Stop %s!" % (bus_num, stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                elif status == -3:
                    output = "Bus *%s* service `not available` at Bus Stop %s!" % (bus_num, stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                # add bus to alerts
                db = getDatabase()
                if db is False:
                    output = "Database down! Please try again later."
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                table = db['bus_alert']
                current_min = time.strftime('%M')
                if table.find_one(chatid=chat_id, ) is None:
                    table.insert(dict(chatid=chat_id, stop_code=stop_code, \
                                      bus_num=bus_num, arrival_min=1, last_alert_min=int(current_min)))
                else:
                    data = dict(chatid=chat_id, stop_code=stop_code, \
                                bus_num=bus_num, arrival_min=1, last_alert_min=int(current_min))
                    table.update(data, ['chatid'])
                output = output + "\nI tell you when Bus %s service reaching Bus Stop %s." % (bus_num, stop_code)
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Please provide a bus stop number followed by a bus service number in the format:\n " + \
                         "*/busarrive 12345 987* for arrival alert when Bus 987 is arriving at Bus Stop 12345"
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busalert':
            if self.checkInputEmpty(chat_id, input) is False:
                # process bus stop number and bus service number
                idx = input.find(' ')
                stop_code = int(input[0:idx])
                input = input[idx + 1:]
                idx = input.find(' ')
                bus_num = input[0:idx]
                bus_num = bus_num.upper()
                arrival_min = int(input[idx + 1:])
                status, output = pollNextBus(stop_code, bus_num, arrival_min)
                if status == 1:  # bus already arriving so alert immediately
                    output = "Bus %s is `arriving now` at Bus Stop %s!" % (bus_num, stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                elif status == 2:  # bus already arriving in less than arrive_min so alert immediately
                    output = output + \
                             "\nBus %s is `arriving in less than %smin` at Bus Stop %s!" \
                             % (bus_num, arrival_min, stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                elif status == -3:
                    output = "Bus %s service `not available` at Bus Stop %s!" % (bus_num, stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                # add bus to alerts
                db = getDatabase()
                if db is False:
                    output = "Database down! Please try again later."
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                    return
                table = db['bus_alert']
                current_min = time.strftime('%M')
                if table.find_one(chatid=chat_id, ) is None:
                    table.insert(dict(chatid=chat_id, stop_code=stop_code, \
                                      bus_num=bus_num, arrival_min=arrival_min, last_alert_min=int(current_min)))
                else:
                    data = dict(chatid=chat_id, stop_code=stop_code, \
                                bus_num=bus_num, arrival_min=arrival_min, last_alert_min=int(current_min))
                    table.update(data, ['chatid'])
                output = output + "\nI tell you when Bus %s service reaching Bus Stop %s in %smin." \
                         % (bus_num, stop_code, arrival_min)
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Please provide a bus stop number followed by a bus service number and alert time in the format:\n " + \
                         "*/busarrive 12345 987 5* for 5min alert before Bus 987 arrives at Bus Stop 12345"
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busstopadd':
            if self.checkInputEmpty(chat_id, input) is False:
                stop_code = input
                if isBusStopValid(stop_code) is True:
                    db = getDatabase()
                    if db is False:
                        output = "Database down! Please try again later."
                        bot.sendMessage(chat_id, output, parse_mode='Markdown')
                        return
                    table_name = str(chat_id) + "_busstoplist"
                    table = db[table_name]
                    if table.find_one(stop=stop_code) is None:
                        table.insert(dict(stop=stop_code))
                        output = "Bus Stop *%s* is added to your bus stop update list." % (stop_code)
                    else:
                        output = "Bus Stop *%s* is already on your bus stop update list." % (stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                else:
                    output = "Bus Stop code %s is `invalid`!" % stop_code
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Please provide a valid Bus Stop code in the format:\n */busstopadd 54321*"
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busstopdelete':
            if self.checkInputEmpty(chat_id, input) is False:
                stop_code = input
                if isBusStopValid(stop_code) is True:
                    db = getDatabase()
                    if db is False:
                        output = "Database down! Please try again later."
                        bot.sendMessage(chat_id, output, parse_mode='Markdown')
                        return
                    table_name = str(chat_id) + "_busstoplist"
                    table = db[table_name]
                    if table.find_one(stop=stop_code) is not None:
                        table.delete(stop=stop_code)
                        output = "Bus Stop *%s* is deleted from your bus stop update list." % (stop_code)
                    else:
                        output = "Bus Stop *%s* is not in your bus stop update list in the first place!" % (stop_code)
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
                else:
                    output = "Bus Stop code %s is `invalid`!" % stop_code
                    bot.sendMessage(chat_id, output, parse_mode='Markdown')
            else:
                output = "Please provide a valid Bus Stop code number in the format:\n */busstopdelete 54321*"
                bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busstoplist':
            output = "Checking list..."
            bot.sendMessage(chat_id, output)
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table_name = str(chat_id) + "_busstoplist"
            table = db[table_name]
            output = "`Saved Bus Stop List`\n"
            for stops in table:
                output = output + str(stops['stop']) + "\n"
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/busstopupdate':
            output = "Checking saved bus stops..."
            bot.sendMessage(chat_id, output)
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table_name = str(chat_id) + "_busstoplist"
            table = db[table_name]
            output = "`Saved Bus Stops`\n\n"
            for stops in table:
                output = output + pollBusStop(stops['stop']) + "\n"
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/train':
            title_msg = "*Train Service Status:*\n"
            isDisrupted, validMsg, output = pollTrainServiceAlerts(title_msg)
            bot.sendMessage(chat_id, output, parse_mode='Markdown')
            return
        elif command == '/subscribetrainalert':
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table = db['train_alert']
            if table.find_one(chatid=chat_id) is None:  # NOT registered yet
                table.insert(dict(chatid=chat_id, prev_output="normal"))
                output = "You are now subscribed to train disruption alerts."
                bot.sendMessage(chat_id, output)
            else:
                output = "You are already subscribed to train disurption alerts!"
                bot.sendMessage(chat_id, output)
            return
        elif command == '/unsubscribetrainalert':
            db = getDatabase()
            if db is False:
                output = "Database down! Please try again later."
                bot.sendMessage(chat_id, output)
                return
            table = db['train_alert']
            if table.find_one(chatid=chat_id) is not None:  # registered
                table.delete(chatid=chat_id)
                output = "You are now unsubscribed from train disruption alerts."
                bot.sendMessage(chat_id, output)
            else:
                output = "You are not subscribed to train disruption alerts in the first place!"
                bot.sendMessage(chat_id, output)
            return
        elif command == '/cancel':
            self.state = 'inactive'
            reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
            output = "Cancelled current operation."
            bot.sendMessage(chat_id, output, reply_markup=reply_markup, parse_mode='Markdown')
            return
        else:
            output = "I do not understand your command."
            bot.sendMessage(chat_id, output)


# Bot Setup
bot = telepot.DelegatorBot(BOT_TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
        per_chat_id(), create_open, SGdataBot, timeout=300),
])
MessageLoop(bot).run_as_thread()

print("Listening...")
while 1:
    time.sleep(5)

    # Rain Alert
    current_min = time.strftime('%M')
    if int(current_min) % 5 == 0 and rain_alert_enable_flag is True:
        rain_alert_enable_flag = False
        title_msg = "`!!Weather Alert!!`\n"
        db = getDatabase()
        if db is not False:
            rain_alert_table = db['rain_alert']
            if isList(rain_alert_table) is True:
                for chatid in rain_alert_table:
                    msg_output = rainUpdate(title_msg, chatid['chatid'])
                    if msg_output != "none":
                        bot.sendMessage(chatid['chatid'], msg_output, parse_mode='Markdown')
    elif int(current_min) % 5 != 0:
        rain_alert_enable_flag = True

    # Train Alert
    if int(current_min) % 5 == 0 and train_alert_enable_flag is True:
        train_alert_enable_flag = False
        title_msg = "`!!Train Status Alert!!`\n"
        db = getDatabase()
        if db is not False:
            train_alert_table = db['train_alert']
            if isList(train_alert_table) is True:
                for chatid in train_alert_table:
                    isDisrupted, validMsg, output = pollTrainServiceAlerts(title_msg)
                    if isDisrupted is True and validMsg is True:
                        if output != chatid['prev_output']:
                            data = dict(chatid=chatid['chatid'], prev_output=output)
                            train_alert_table.update(data, ['chatid'])
                            bot.sendMessage(chatid['chatid'], output, parse_mode='Markdown')
                    else:
                        # assume train resume service after disurption if prev_output not "normal"
                        if chatid['prev_output'] != "normal":
                            data = dict(chatid=chatid['chatid'], prev_output="normal")
                            train_alert_table.update(data, ['chatid'])
                            bot.sendMessage(chatid['chatid'], output, parse_mode='Markdown')
    elif int(current_min) % 5 != 0:
        train_alert_enable_flag = True

    # Bus Arrival Alert
    if True:
        db = getDatabase()
        if db is not False:
            bus_alert_table = db['bus_alert']
            if isList(bus_alert_table) is True:
                for bus_alert in bus_alert_table:
                    last_alert_min = bus_alert['last_alert_min']
                    if last_alert_min == int(current_min):
                        continue
                    stop_code = bus_alert['stop_code']
                    bus_num = bus_alert['bus_num']
                    arrival_min = bus_alert['arrival_min']
                    status, output = pollNextBus(stop_code, bus_num, arrival_min)
                    if status == 1:
                        output = "Bus %s is `arriving now` at Bus Stop %s!" % (bus_num, stop_code)
                    elif status == 2:
                        output = "Bus %s is `arriving in %smin` at Bus Stop %s!" % (bus_num, arrival_min, stop_code)
                    elif status == -1:
                        output = "Bus %s at Bus Stop %s has `ended service`!" % (bus_num, stop_code)
                    elif status == -2:
                        output = "Bus %s arriving at Bus Stop %s is `FULL`!" % (bus_num, stop_code)
                    else:
                        data = dict(chatid=bus_alert['chatid'], stop_code=stop_code, bus_num=bus_num, \
                                    arrival_min=arrival_min, last_alert_min=int(current_min))
                        bus_alert_table.update(data, ['chatid'])
                        continue
                    bot.sendMessage(bus_alert['chatid'], output, parse_mode='Markdown')
                    bus_alert_table.delete(chatid=bus_alert['chatid'])
