import re
import json
import requests
import numpy as np
from nltk.tag import StanfordNERTagger

def get_weather_data(request):

    stanford_ner_dir = '/home/shreeya/Desktop/CMPE-295/cmpe_295/stanford-ner-2014-06-16/'
    eng_model_filename= stanford_ner_dir + 'classifiers/english.all.3class.distsim.crf.ser.gz'
    my_path_to_jar= stanford_ner_dir + 'stanford-ner.jar'

    st = StanfordNERTagger(model_filename=eng_model_filename, path_to_jar=my_path_to_jar)
    tags = st.tag(request.split())

    print tags

    print "Inside Weather"
    print "Request: " + request
    weather_json = ""

    default_place = "San Jose"
    response = {}
    response_text = ""

    place = ""
    found  = False
    for tag in tags:
        if tag[1] == "LOCATION":
            found = True
            place = place + tag[0] + " "

    if not found:
        word = ""
        keywords = [" in ", " at ", " of "]
        for keyword in keywords:
            if keyword in request.lower():
                word = keyword

        if len(word):
            print word
            pat = re.compile(r"(?<=" + re.escape(word) + r").*$")
            res = re.search(pat,request)
            place = res.group()
            print place
        else:
            place = default_place

    print "Place : ", place
    try:
        weather_json = requests.get("http://api.openweathermap.org/data/2.5/weather?q="+place+"&APPID=xxx").json()

        if len(weather_json)==0:
            response_text = "Your weather details could not be found! Please try again later."
            response_status = 0
        elif weather_json['cod'] == u'404':
            response_text = "Your city could not be found! Please try again."
            response_status = 0
        else:
            temp = str(float(weather_json["main"]["temp"])*(9.0/5) - 459.67)
            min_temp = str(float(weather_json["main"]["temp_min"])*(9.0/5) - 459.67)
            max_temp = str(float(weather_json["main"]["temp_max"])*(9.0/5) - 459.67)

            response_text = "The weather in "+place+" is " +weather_json["weather"][0]["main"]+ " with "+ weather_json["weather"][0]["description"]
            response_text += " The temperature is "+temp + " fahrenheit with a high of " + max_temp + " fahrenheit and a low of "+ min_temp + " fahrenheit."
            response_status = 1

        if (("rain" or "rainy") in request.lower()):
            if "rain" in weather_json:
                response_text += " It will probably rain today!"
            else:
                response_text += " It will probably not rain today!"

        if (("snow" or "snowy") in request.lower()):
            if "snow" in weather_json:
                response_text += " It will probably snow today!"
            else:
                response_text += " It will probably not snow today!"

        if (("cloud" or "cloudy") in request.lower()):
            if "clouds" in weather_json:
                response_text += " It will be cloudy today!"
            else:
                response_text += " It will not be cloudy today!"

        if (("sun" or "sunny") in request.lower()):
            if "sun" in weather_json:
                response_text += " It will be sunny today!"
            else:
                response_text += " It will not be sunny today!"
    except:
        response_text = "Your weather data cannot be obtained at the moment. Please try again later."
        response_status = 0

    print "Response : " + response_text

    response['response_text'] = response_text
    response['response_status'] = response_status

    return response

'''
# unit test
get_weather_data("what is the weather in Bangalore")
get_weather_data("what is the weather now")
get_weather_data("xxx")
get_weather_data("what is the weather in xxx")

get_weather_data("will it rain today")
get_weather_data("will it be cloudy today")
'''
