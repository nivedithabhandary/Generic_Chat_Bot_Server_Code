import re
import json
import requests
import numpy as np
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

'''
https://food2fork.com
API Key:xxx
'''

def get_food_data(request):
    print "Inside Food"
    print "Request: " + request

    response = {}
    response_text = ""
    food_json = ""

    tokenized_request = sent_tokenize(request)
    tagged = []
    food_name = ""
    for i in tokenized_request:
        words = nltk.word_tokenize(i)
        tagged = nltk.pos_tag(words)

    for elem in tagged:
        if (elem[1] == "NNP" or elem[1] == "NN") and elem[0]!="recipe" :
            food_name = food_name + " " +elem[0]

    if "cook" in request:
        pat = re.compile(r'(?<=cook ).*$')
        res = re.search(pat,request)
        name = res.group()
        if name != food_name:
            food_name = name

    try:
        food_json = requests.get("http://food2fork.com/api/search?key=xxx&q="+food_name).json()


    except:
        response_text = "Recipes cannot be retrieved at the moment. Please try again later."
        response_status = 0

    print "Response : " + response_text

    response['response_text'] = response_text
    response['response_status'] = response_status

    return response
