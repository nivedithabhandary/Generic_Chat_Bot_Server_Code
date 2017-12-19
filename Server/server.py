'''
Python Flask based server to recieve GET requests from Raspberry PI
end device and send POST response
'''

import re
import sys
import json
import random
import datetime
import numpy as np
import nltk.tokenize
import requests
from flask import request
import pickle
# Classifiers
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.ensemble import VotingClassifier
# Cross validation
from sklearn import linear_model
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_predict, cross_val_score
from sklearn import metrics
# Convert text to vector
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from flaskext.mysql import MySQL

#For natural language processing
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

from googleplaces import GooglePlaces, types, lang

#For movie recommendations
from Movie_Recommendation.movie import MovieRecommender

from News.news import *
import News.news as news
from Weather.weather import *
import Weather.weather as weather
from Food.food import *
import Food.food as food

from flask import Flask
app = Flask(__name__)

mysql = MySQL()

# MySQL configurations

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'smart123'
app.config['MYSQL_DATABASE_DB'] = 'PythonTest'
app.config['MYSQL_DATABASE_HOST'] = 'xxx'
mysql.init_app(app)
#conn = mysql.connect()

train_file = "train.dat"
error = "Content not found"
error2 = " Request could not be satisfied. Please try again. "

debug_mode = False

def _preprocess(filename):
    # Open train file in read mode and read all lines
    with open(filename, "r") as fh:
        lines = fh.readlines()

    labels = []
    features = []
    for line in lines:
        (label, feature) = re.sub(r'[^\w]',' ', line).split(None,1)
        labels.append(label)
        features.append(feature)

    return features, labels

def _classifier(test_features):

    if debug_mode:
        count_vect = CountVectorizer()
        tfidf_transformer = TfidfTransformer()
        train_features, labels = _preprocess(train_file)

        # To convert text to feature vectors
        # SRC: http://scikit-learn.org/stable/tutorial/text_analytics/working_with_text_data.html
        X_train_counts = count_vect.fit_transform(train_features)
        tf_transformer = TfidfTransformer(use_idf=False).fit(X_train_counts)
        X_train_tf = tf_transformer.transform(X_train_counts)
        X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)

        pickle.dump(tfidf_transformer, open( "tfidf_transformer.p", "wb" ))
        pickle.dump(count_vect, open("count_vect.p","wb"))
    else:
        count_vect = pickle.load(open("count_vect.p", 'rb'))
        tfidf_transformer = pickle.load(open("tfidf_transformer.p", 'rb'))

    # Fit test data
    X_test_counts = count_vect.transform(nltk.sent_tokenize(test_features))
    X_test_tfidf = tfidf_transformer.transform(X_test_counts)

    if debug_mode:
        names = ["KNN", "Decision Tree", "SVM", "Naive Bayes"]
        classifiers = [KNeighborsClassifier(n_neighbors=3, weights='distance'),
        DecisionTreeClassifier(random_state=0),
        SVC(kernel="linear", C=1.0, probability=True),
        MultinomialNB()
        ]

        classifier_types = []
        for name, clf in zip(names, classifiers):
            clf.fit(X_train_tfidf, labels)
            label_predicted_for_test = clf.predict(X_test_tfidf)
            classifier_types.append((name, clf))
            #print "\n\n"
            #print "Predict Probability: " + name
            #print clf.predict_proba(X_test_tfidf)

        print "\nEnsemble classifier output: "
        eclf1 = VotingClassifier(estimators=classifier_types, voting='soft', weights=[1,1,2,1])
        eclf1 = eclf1.fit(X_train_tfidf, labels)

        pickle.dump(eclf1, open("voting_classifier_object.p","wb"))

    else:
        eclf1 = pickle.load(open("voting_classifier_object.p", 'rb'))

    #print "\n\nPredict Proba values : "
    #print eclf1.predict_proba(X_test_tfidf)
    ensemble_label = eclf1.predict(X_test_tfidf)
    print ensemble_label

    return ensemble_label[0]

def _store_in_db(timestamp, request, intent):

    return 'Stored contents to DB'


def _get_synonyms_for_recommend():
    synonyms = []
    for syn in wordnet.synsets("recommend"):
        for l in syn.lemmas():
            synonyms.append(l.name())
    return synonyms


@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/request')
def show_request():

    _request = request.args.get('text')
    _userid = request.args.get('user')

    _request = re.sub('[^A-Za-z0-9 ]+', '', _request)
    print _request, _userid

    # Time at which the request was made
    timestamp = str(datetime.datetime.now())

    # Get the intent of the request
    intent = _classifier(_request)

    # Generate Response
    '''
    Response format :
    response['response_type']  = "Information" or "Recommendation" or "Fallback"
    response['response_category'] = "Time" or "Metadata" or "Weather" or "Music" or "Movie" or "Place" or "Food" or "News" or "WolframAlpha"
    response['response_status'] = 1 for success, 0 for failure
    '''
    response = {}
    movie_recommendations = []
    response['response_status'] = 0

    try:
        if intent == "Time":
            response['response_text'] = "Time is " + str(datetime.datetime.now())
            response['response_type'] = "Information"
            response['response_status'] = 1
            response['response_category'] = "Time"

        elif intent == "Metadata":
            print "Inside Metadata \n"

            response_text = "I am Priya, a voice controlled family assistant. Created by students of San Jose State University."
            response_text += " I can tell time, weather updates, read news. Give recommendations on music, movie, places to visit and much more. "
            response_text += "You could say, "

            commands = [" Who is CEO of Facebook?"," What is meaning of Whimsical?"," Tell me about movie Avatar.", " Recommend me a movie.", " Whats new?"," How is the weather in San Jose?", " Play top songs from India"," What is the population of USA?"," What is capital of Greece?"," Who invented Camera?"," what is square root of ten?"]
            random.shuffle(commands)

            questions = "".join(c for c in commands[0:2])
            response_text += questions
            response_text += " What would you like to ask? "

            response['response_text'] = response_text
            response['response_type'] = "Information"
            response['response_status'] = 1
            response['response_category'] = "Metadata"

        elif intent == "Weather":

            output = weather.get_weather_data(_request)

            response['response_text'] = output['response_text']
            response['response_category'] = "Weather"
            response['response_type'] = "Information"
            response['response_status'] = output['response_status']

        elif intent == "Movie":

            print "Inside movies"

            conn = mysql.connect()
            cur = conn.cursor()
            select_stmt = "SELECT * FROM tbl_user WHERE user_name = %(user_id)s"
            cur.execute(select_stmt, { 'user_id': _userid })
            rows = cur.fetchone()
            cur.close()

            twitter_username = ""
            movie_history_list = []
            tag_list = []
            print "\n\n Row:"
            print rows
            print "\n\n"
            if rows != None:
                twitter_username = rows[4]
                movie_history_list = rows[7].split(',')
                tag_list = rows[6].split(',')

            print twitter_username, movie_history_list, tag_list
            '''
            movie_history_list = ["Tomorrowland (2015)","You Only Live Twice (1967)","Southland Tales (2006)","Money Train (1995)","Four Rooms (1995)"]
            tag_list = ["adventure", "feel good", "life", "new york city", "police"]
            twitter_username = "realDonaldTrump"
            '''
            obj = MovieRecommender()
            output = obj.get_movies(_request, username=twitter_username, movie_history_list=movie_history_list, tag_list=tag_list)

            response['response_text'] = output['response_text']
            response['response_category'] = "Movie"
            response['response_type'] = output['response_type']
            response['response_status'] = output['response_status']

        elif intent == "Places":
            API_KEY= 'xxx'
            google_places = GooglePlaces(API_KEY)

            query_result = google_places.text_search(query=_request, language='en',radius=20000)

            places_result = "You can visit"

            if query_result is not None:
                for place in query_result.places:
                    # Returned places from a query are place summaries.
                    places_result+= " "+ place.name

            print "Inside place"
            response['response_text'] = places_result
            response['response_category'] = "Place"
            response['response_type'] = "Information"
            response['response_status'] = 1

        elif intent == "Food":

            output = food.get_food_data(_request)
            #output = {}
            # Get recipe for the particular food_name
            response['response_text'] = output['response_text']
            response['response_category'] = "Food"
            response['response_type'] = "Information"
            response['response_status'] = output['response_status']

        elif intent == "News":

            output = news.get_news(_request)

            response['response_text'] = output['response_text']
            response['response_category'] = "News"
            response['response_type'] = "Information"
            response['response_status'] = output['response_status']

        elif intent == "Fallback":
            response['response_text'] = _request
            response['response_category'] = "Fallback"
            response['response_type'] = "WolframAlpha"
            response['response_status'] = 0

        else:
            response['response_text'] = error
            response['response_category'] = "Not Found"
            response['response_status'] = 0
    except:
            print "\n\n Unexpected error:", sys.exc_info()[0]
            response['response_text'] = _request + error2
            response['response_category'] = intent
            response['response_status'] = 0

    json_response = json.dumps(response)
    _store_in_db(timestamp, _request, intent)

    return json_response, 200
