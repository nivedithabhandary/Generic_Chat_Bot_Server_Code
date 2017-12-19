import re
import json
import requests
import numpy as np

def get_news(request):

    print "Inside News"
    news_json = ""
    news_articles = "Here is your "
    response = {}

    if "technology" in request.lower():
        print "tech news"
        news_articles = news_articles + "Technology news "
        news_json = requests.get("https://newsapi.org/v1/articles?source=techcrunch&apiKey=xxx").json()
    else:
        print "USA today"
        news_articles = news_articles + "Flash Briefing "
        news_json = requests.get("https://newsapi.org/v1/articles?source=usa-today&apiKey=xxx").json()

    news_index = np.random.permutation(len(news_json['articles'])-1)

    if ("headline" or "headlines") in request.lower():
        # 1,len(news_json['articles'])
        for i in news_index[0:3]:
            title = news_json['articles'][i]['title']
            news_articles = news_articles + " Title: " + title
    else:
        for i in news_index[0:3]:
            title = news_json['articles'][i]['title']
            description = news_json['articles'][i]['description']
            news_articles = news_articles + " News Title: " + title + " Description is: " + description

    response['response_text'] = news_articles
    response['response_category'] = "News"
    response['response_status'] = 1

    return response
