#
# config for Loxone Weather Gateway
#

host = '::'
port = 8088
debug = True
# cache_timeout=300 # 5 minutes

owm_token = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
owm_weather_api_url = 'http://api.openweathermap.org/data/2.5/weather'
owm_onecall_api_url = 'http://api.openweathermap.org/data/2.5/onecall'
owm_forecast_api_url = 'http://api.openweathermap.org/data/2.5/forecast'

loxone_token = 'loxone_XXXXXXXXXXXX'

picto_codes = {
    '200': '28',
    '201': '27',
    '202': '30',
    '210': '28',
    '211': '27',
    '212': '30',
    '221': '30',
    '230': '28',
    '231': '27',
    '232': '30',

    '300': '33',
    '301': '33',
    '302': '33',
    '310': '23',
    '311': '23',
    '312': '23',
    '313': '25',
    '314': '25',
    '321': '25',

    '500': '33',
    '501': '23',
    '502': '25',
    '503': '25',
    '504': '25',
    '511': '25',
    '520': '25',
    '521': '25',
    '522': '25',
    '531': '25',

    '600': '34',
    '601': '24',
    '602': '26',
    '611': '26',
    '612': '35',
    '613': '35',
    '615': '35',
    '616': '35',
    '620': '35',
    '621': '35',
    '622': '35',

    '701': '5',
    '711': '5',
    '721': '5',
    '731': '5',
    '741': '5',
    '751': '5',
    '761': '5',
    '762': '5',
    '771': '5',
    '781': '5',

    '800': '1',

    '801': '3',
    '802': '4',
    '803': '7',
    '804': '19'
}
