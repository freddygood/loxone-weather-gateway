#!/usr/bin/env python

from flask import Flask, Response, request, abort
# from flask_caching import Cache

from xml.dom.minidom import parse, parseString
from xml.parsers.expat import ExpatError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import json
import dicttoxml
import sys
import os
import time
import requests

import config as config

# owm links
# http://api.openweathermap.org/data/2.5/onecall?lang=en&lon=4.6490&units=metric&APPID=23b6e837ee043c7efa6ba2789772fd8b&lat=52.3760&exclude=minutely%2Calerts
# http://api.openweathermap.org/data/2.5/forecast?lat=52.3760&units=metric&lon=4.6490&lang=en&APPID=23b6e837ee043c7efa6ba2789772fd8b

# loxone link
# /forecast/?user=loxone_504F94A02160&coord=4.6490,52.3760&asl=2&format=1&new_api=1

host = getattr(config, 'host')
port = getattr(config, 'port')
debug = getattr(config, 'debug')
# cache_timeout = getattr(config, 'cache_timeout')

owm_token = getattr(config, 'owm_token')
owm_weather_api_url = getattr(config, 'owm_weather_api_url')
owm_onecall_api_url = getattr(config, 'owm_onecall_api_url')
owm_forecast_api_url = getattr(config, 'owm_forecast_api_url')

picto_codes = getattr(config, 'picto_codes')

loxone_token = getattr(config, 'loxone_token')

application = Flask(__name__)
# cache = Cache(application, config={'CACHE_TYPE': 'simple'})

@application.route('/forecast/', methods=['GET'])
# @cache.memoize(timeout=cache_timeout)
def get_weather():

    user = request.args.get('user', type = str)
    coord = request.args.get('coord', type = str)
    asl = request.args.get('asl', type = str)
    orig = request.args.get('orig', type = str)

    try:
        assert user != None, 'user is mandatory parameter'
        assert coord != None, 'coord is mandatory parameter'
        assert asl != None, 'asl is mandatory parameter'
        assert user == loxone_token, 'wrong loxone token'

    except AssertionError as e:
        application.logger.error(e, exc_info=True)
        abort(400)
    except Exception as e:
        application.logger.error('Error happened: {0}'.format(e.message))
        abort(502)

    (lon, lat) = coord.split(',')
    application.logger.debug('Found coordinates lat: {0}, lon: {1}'.format(lat, lon))

    payload_onecall = { 'lat': lat, 'lon': lon, 'units': 'metric', 'exclude': 'minutely,alerts', 'lang': 'en', 'APPID': owm_token }

    onecall = requests.get(owm_onecall_api_url, params = payload_onecall)
    application.logger.debug('OWM OneCall URL has been called "{0}"'.format(onecall.url))

    payload_forecast = { 'lat': lat, 'lon': lon, 'units': 'metric', 'lang': 'en', 'APPID': owm_token }

    forecast = requests.get(owm_forecast_api_url, params = payload_forecast)
    application.logger.debug('OWM Forecast URL has been called "{0}"'.format(forecast.url))

    if orig == None:
        exp_date = date.today() + relativedelta(months=+1)
        application.logger.debug('Expiration date {0}'.format(exp_date))

        weather = json.loads(onecall.text)
        weather_f = json.loads(forecast.text)

        timezone_name = weather['timezone']
        timezone_offset = int(weather['timezone_offset'])/60/60

        tz = timezone(timezone_name)

        os.environ['TZ'] = timezone_name
        time.tzset()

        sunrise = datetime.fromtimestamp(weather['current']['sunrise']).strftime('%H:%M')
        sunset = datetime.fromtimestamp(weather['current']['sunset']).strftime('%H:%M')

        if lon < 0:
            lon = -lon
            e_w = 'W'
        else:
            e_w = 'E'

        if lat < 0:
            lat = -lat
            n_s = 'S'
        else:
            n_s = 'N'

        response = ''
        response += '<mb_metadata>\n'
        response += 'id;name;longitude;latitude;height (m.asl.);country;timezone;utc-timedifference;sunrise;sunset;\n'
        response += 'local date;weekday;local time;temperature(C);feeledTemperature(C);windspeed(km/h);winddirection(degr);wind gust(km/h);low clouds(%);medium clouds(%);high clouds(%);precipitation(mm);probability of Precip(%);snowFraction;sea level pressure(hPa);relative humidity(%);CAPE;picto-code;radiation (W/m2);\n'
        response += '</mb_metadata><valid_until>{0}</valid_until>\n'.format(exp_date)
        response += '<station>\n'
        response += ';Haarlem;{0}{1};{2}{3};{4};The Netherlands;{5};UTC+{6};{7};{8};\n'.format(lon, e_w, lat, n_s, asl, timezone_name, timezone_offset, sunrise, sunset)

        application.logger.debug('Found {0} entries in hourly OneCall call'.format(len(weather['hourly'])))
        application.logger.debug('Found {0} entries in 3-hourly Forecast call'.format(len(weather_f['list'])))

        station = []

        uv_rad = {}

        for d in weather['daily']:
            datetime_ts = datetime.fromtimestamp(d['dt'])
            day = datetime_ts.strftime('%d.%m.%Y')
            uv_rad[day] = round(d['uvi'] * 18.9, 0)

        application.logger.debug('Found {0} entries for solar radiation'.format(len(uv_rad)))


        for d in weather['hourly']:

            datetime_ts = datetime.fromtimestamp(d['dt'])
            day = datetime_ts.strftime('%d.%m.%Y')
            day_week = datetime_ts.strftime('%a')
            hour = datetime_ts.strftime('%H')
            index = datetime_ts.strftime('%d/%m/%Y:%H')

            datetime_ts_latest = datetime_ts
#            application.logger.debug('Processing {0} from OneCall'.format(index))

            picto_code_id = str(d['weather'][0]['id'])
            picto_code = picto_codes[picto_code_id] if picto_code_id in picto_codes else '1'

            # convert wind from m/s to km/h
            wind_speed = round(d['wind_speed'] * 3.6, 1)
            wind_gust = round(d['wind_gust'] * 3.6, 1) if 'wind_gust' in d else '0'

            percipitation_1h = 0
            if 'rain' in d and '1h' in d['rain']:
                percipitation_1h =+ d['rain']['1h']
            if 'snow' in d and '1h' in d['snow']:
                percipitation_1h =+ d['snow']['1h']

            station.append({
                'day': day,
                'day_week': day_week,
                'hour': hour,
                'temp': d['temp'],
                'feels_like': d['feels_like'],
                'wind_speed': wind_speed,
                'wind_deg': d['wind_deg'],
                'wind_gust': wind_gust,
                'clouds_low': 0,
                'clouds_mid': d['clouds'],
                'clouds_high': 0,
                'percip_1h': percipitation_1h,
                'pop': d['pop'],
                'snow_fraction': 0,
                'pressure': d['pressure'],
                'humidity': d['humidity'],
                'cape': 0,
                'picto_code': picto_code,
                'uv_rad': uv_rad[day] if day in uv_rad else 0
            })


        weather_f_1h = []
        weather_f_init = True

        for d in weather_f['list']:

            if weather_f_init:
                datetime_ts_0 = d['dt']
                temp_0 = d['main']['temp']
                feels_like_0 = d['main']['feels_like']
                wind_speed_0 = round(d['wind']['speed'] * 3.6, 1)
                wind_deg_0 = d['wind']['deg']
                wind_gust_0 = round(d['wind']['gust'] * 3.6, 1) if 'wind' in d else '0'
                pressure_0 = d['main']['pressure']
                humidity_0 = d['main']['humidity']
                clouds_0 = d['clouds']['all']
                pop_0 = d['pop']
                rain_0 = d['rain']['3h'] / 3 if 'rain' in d else 0
                snow_0 = d['snow']['3h'] / 3 if 'snow' in d else 0
                percip_1h_0 = round(rain_0 + snow_0, 2)
                picto_code_id_0 = str(d['weather'][0]['id'])
                picto_code_0 = picto_codes[picto_code_id_0] if picto_code_id_0 in picto_codes else '1'

                weather_f_init = False
                continue


#            application.logger.debug('Processing entry 1/3: timestamp {0}, temp {1}'.format(datetime_ts_0, temp_0))
            weather_f_1h.append({
              'dt': datetime_ts_0,
              'temp': temp_0,
              'feels_like': feels_like_0,
              'wind_speed': wind_speed_0,
              'wind_deg': wind_deg_0,
              'wind_gust': wind_gust_0,
              'pressure': pressure_0,
              'humidity': humidity_0,
              'clouds': clouds_0,
              'pop': pop_0,
              'percip_1h': percip_1h_0,
              'picto_code': picto_code_0
            })


            datetime_ts = d['dt']
            temp = d['main']['temp']
            feels_like = d['main']['feels_like']
            wind_speed = round(d['wind']['speed'] * 3.6, 1)
            wind_deg = d['wind']['deg']
            wind_gust = round(d['wind']['gust'] * 3.6, 1) if 'wind' in d else '0'
            pressure = d['main']['pressure']
            humidity = d['main']['humidity']
            clouds = d['clouds']['all']
            pop = d['pop']


            datetime_ts_1 = datetime_ts_0 + 3600
            temp_1 = round(temp_0 + ( temp - temp_0 ) / 3, 2)
            feels_like_1 = round(feels_like_0 + ( feels_like - feels_like_0 ) / 3, 2)
            wind_speed_1 = round(wind_speed_0 + ( wind_speed - wind_speed_0 ) / 3, 1)
            wind_deg_1 = round(wind_deg_0 + ( wind_deg - wind_deg_0 ) / 3, 0)
            wind_gust_1 = round(wind_gust_0 + ( wind_gust - wind_gust_0 ) / 3, 1)
            pressure_1 = round(pressure_0 + ( pressure - pressure_0 ) / 3, 0)
            humidity_1 = round(humidity_0 + ( humidity - humidity_0 ) / 3, 0)
            clouds_1 = round(clouds_0 + ( clouds - clouds_0 ) / 3, 0)
            pop_1 = round(pop_0 + ( pop - pop_0 ) / 3, 0)

#            application.logger.debug('Processing entry 2/3: timestamp {0}, temp {1} ({2} -> {3})'.format(datetime_ts_1, temp_1, temp_0, temp))
            weather_f_1h.append({
              'dt': datetime_ts_1,
              'temp': temp_1,
              'feels_like': feels_like_1,
              'wind_speed': wind_speed_1,
              'wind_deg': wind_deg_1,
              'wind_gust': wind_gust_1,
              'pressure': pressure_1,
              'humidity': humidity_1,
              'clouds': clouds_1,
              'pop': pop_1,
              'percip_1h': percip_1h_0,
              'picto_code': picto_code_0
            })


            datetime_ts_2 = datetime_ts_0 + 7200
            temp_2 = round(temp_0 + ( temp - temp_0 ) / 3 * 2, 2)
            feels_like_2 = round(feels_like_0 + ( feels_like - feels_like_0 ) / 3 * 2, 2)
            wind_speed_2 = round(wind_speed_0 + ( wind_speed - wind_speed_0 ) / 3 * 2, 1)
            wind_deg_2 = round(wind_deg_0 + ( wind_deg - wind_deg_0 ) / 3 * 2, 0)
            wind_gust_2 = round(wind_gust_0 + ( wind_gust - wind_gust_0 ) / 3 * 2, 1)
            pressure_2 = round(pressure_0 + ( pressure - pressure_0 ) / 3 * 2, 0)
            humidity_2 = round(humidity_0 + ( humidity - humidity_0 ) / 3 * 2, 0)
            clouds_2 = round(clouds_0 + ( clouds - clouds_0 ) / 3 * 2, 0)
            pop_2 = round(pop_0 + ( pop - pop_0 ) / 3 * 2, 0)

#            application.logger.debug('Processing entry 3/3: timestamp {0}, temp {1} ({2} -> {3})'.format(datetime_ts_2, temp_2, temp_0, temp))
            weather_f_1h.append({
              'dt': datetime_ts_2,
              'temp': temp_2,
              'feels_like': feels_like_2,
              'wind_speed': wind_speed_2,
              'wind_deg': wind_deg_2,
              'wind_gust': wind_gust_2,
              'pressure': pressure_2,
              'humidity': humidity_2,
              'clouds': clouds_2,
              'pop': pop_2,
              'percip_1h': percip_1h_0,
              'picto_code': picto_code_0
            })

            datetime_ts_0 = d['dt']
            temp_0 = d['main']['temp']
            feels_like_0 = d['main']['feels_like']
            wind_speed_0 = d['wind']['speed'] * 3.6
            wind_deg_0 = d['wind']['deg']
            wind_gust_0 = d['wind']['gust'] if 'wind' in d else '0'
            pressure_0 = d['main']['pressure']
            humidity_0 = d['main']['humidity']
            clouds_0 = d['clouds']['all']
            pop_0 = d['pop']
            rain_0 = d['rain']['3h'] / 3 if 'rain' in d else 0
            snow_0 = d['snow']['3h'] / 3 if 'snow' in d else 0
            percip_1h_0 = round(rain_0 + snow_0, 2)
            picto_code_id_0 = str(d['weather'][0]['id'])
            picto_code_0 = picto_codes[picto_code_id_0] if picto_code_id_0 in picto_codes else '1'


        for d in weather_f_1h:
            datetime_ts = datetime.fromtimestamp(d['dt'])
            day = datetime_ts.strftime('%d.%m.%Y')
            day_week = datetime_ts.strftime('%a')
            hour = datetime_ts.strftime('%H')
            index = datetime_ts.strftime('%d/%m/%Y:%H')

            if datetime_ts > datetime_ts_latest:
#                application.logger.debug('Processing {0} from 3-hourly Forecast'.format(index))

                station.append({
                    'day': day,
                    'day_week': day_week,
                    'hour': hour,
                    'temp': d['temp'],
                    'feels_like': d['feels_like'],
                    'wind_speed': d['wind_speed'],
                    'wind_deg': d['wind_deg'],
                    'wind_gust': d['wind_gust'],
                    'clouds_low': 0,
                    'clouds_mid': d['clouds'],
                    'clouds_high': 0,
                    'percip_1h': d['percip_1h'],
                    'pop': d['pop'],
                    'snow_fraction': 0,
                    'pressure': d['pressure'],
                    'humidity': d['humidity'],
                    'cape': 0,
                    'picto_code': picto_code,
                    'uv_rad': uv_rad[day] if day in uv_rad else 0
                })

#            else:
#                application.logger.debug('Skipping {0} from 3-hourly Forecast'.format(index))


        for s in station:

# local date;weekday;local time;temperature(C);feeledTemperature(C);windspeed(km/h);winddirection(degr);wind gust(km/h);
# low clouds(%);medium clouds(%);high clouds(%);precipitation(mm);probability of Precip(%);snowFraction;
# sea level pressure(hPa);relative humidity(%);CAPE;picto-code;radiation (W/m2);

            response += '{0};{1};{2};{3};{4};'.format(s['day'], s['day_week'], s['hour'], s['temp'], s['feels_like'])
            response += '{0};{1};{2};'.format(s['wind_speed'], s['wind_deg'], s['wind_gust'])
            response += '{0};{1};{2};'.format(s['clouds_low'], s['clouds_mid'], s['clouds_high'])
            response += '{0};{1};{2};'.format(s['percip_1h'], s['pop'], s['snow_fraction'])
            response += '{0};{1};{2};{3};{4};\n'.format(s['pressure'], s['humidity'], s['cape'], s['picto_code'], s['uv_rad'])

        response += '</station>\n'

        return Response(response, mimetype='text/xml')
    else:
        return Response(r.text, mimetype='application/json')

@application.route('/')
def default_route():
    response = Response()
    response.status_code = 404
    return response

if __name__ == "__main__":
    application.run(debug=debug, host=host, port=port)
