import re
import json
import os.path
import requests
import threading
#import urllib.request
import DataService
import imdbUtil
from functools import partial
from movieRecommend import MovieRecommend
#For natural language processing
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

# Global variable of User information. Must be replaced with values from web app
_movie_history_list = ["Tomorrowland (2015)","You Only Live Twice (1967)","Southland Tales (2006)","Money Train (1995)","Four Rooms (1995)"]
_tag_list = ["stand up comedy","interracial romance","mad scientist","space travel"]
_twitter_username = "nivedithapb"

class MovieRecommender:

	def __init__(self):
		self.mongo = DataService.Mongo("imdb")

	def preprocess(self, movie_title):
		movie_title = re.sub('[^A-Za-z ]+', '', movie_title)
		return movie_title

	def process_twitter_recommendation(self, username):
		print(username)

		recommendations = []
		result = ""
		recommender = MovieRecommend(self.mongo)
		all_recommendations = recommender.recommend_movies_for_twitter_integrated(username)
		total = min(5, len(all_recommendations))
		for i in range(total):
			recommendations.append(all_recommendations[i])

		# Process obtained recommendations
		print("\n\nFound recommendations from Twitter: ")
		print (recommendations)

		for rec in recommendations:
			result += self.preprocess(rec)
			result += ", "
		return result

	def process_movie_history_recommendation(self, movie_history_list):
		print (movie_history_list)
		result = ""

		recommendations = []
		recommender = MovieRecommend(self.mongo)
		all_recommendations = recommender.recommend_movies_based_on_history(movie_history_list)
		all_recommendations = recommender.get_titles_by_mids(all_recommendations)
		total = min(5, len(all_recommendations))
		for i in range(total):
			recommendations.append(all_recommendations[i])

		# Process obtained recommendations
		print("\n\nFound recommendations from Movie History: ")
		print (recommendations)

		for rec in recommendations:
			result += self.preprocess(rec)
			result += ", "
		return result

	def process_tag_recommendation(self, tag_list):
		print (tag_list)
		result = ""

		recommendations = []
		recommender = MovieRecommend(self.mongo)
		all_recommendations = recommender.recommend_movies_based_on_tags_integrated(tag_list)
		total = min(5, len(all_recommendations))
		for i in range(total):
			recommendations.append(all_recommendations[i])

		# Process obtained recommendations
		print("\n\nFound recommendations from Tags: ")
		print (recommendations)

		for rec in recommendations:
			result += self.preprocess(rec)
			result += ", "
		return result

	def process_popular_movies(self):
		result = ""

		recommendations = []
		recommender = MovieRecommend(self.mongo)
		all_recommendations = recommender.recommend_movies_based_on_popularity()
		total = min(5, len(all_recommendations))
		for i in range(total):
			recommendations.append(all_recommendations[i])

		# Process obtained recommendations
		print("\n\nFound Most popular movies ")
		print (recommendations)

		for rec in recommendations:
			result += self.preprocess(rec)
			result += ", "
		return result

	def get_synonyms_for_recommend(self):
		synonyms = []
		for syn in wordnet.synsets("recommend"):
			for l in syn.lemmas():
				synonyms.append(l.name())
		return synonyms

	def get_details(self, movie):
		preprocessed = movie.replace(" ","+")
		resp = requests.get("http://www.omdbapi.com/?t="+preprocessed+"&apikey=fc9b05bb")
		result = json.loads(resp.text)
		response_status = 0
		response_text = ""

		if "Error" in result:
			response_status = 0
			response_text = result["Error"]
		else:
			response_text = "Here is some information about "+movie+"."\
			" The plot of the Movie is "+result['Plot']+"."\
			" The actors in the Movie are "+result['Actors']+"."\
			" The genre is "+result['Genre']+"."

			if result['imdbRating']=="N/A":
				response_text += " The IMDB rating is not available. "
			elif float(result['imdbRating']) > 7:
				response_text = response_text + " This movie has got high IMDB rating of "\
				+result['imdbRating'] +" You should watch it."
			else:
				response_text = response_text + " This movie has not got a high IMDB rating. Its only "\
						+result['imdbRating'] +" Mind before you watch it."

			response_status = 1

		return response_text, response_status

	def get_movies(self, request, username = "", movie_history_list = [], tag_list = []):
		response = {}
		output = ""

		for syn in self.get_synonyms_for_recommend():
			if syn in request:
				# Recommend me movies based on my twitter profile
				if username != "":
					response_text = "Here are your recommended movies from your twitter id. "
					output = self.process_twitter_recommendation(username)
					if output == "":
						response["response_text"] = "Sorry we couldn't find any movie recommendations for your twitter profile. "
						response["response_status"] = 0
					else:
						response["response_text"] = response_text + output
						response["response_status"] = 1

					response['response_type'] = "Recommendation"
					return response

				# Recommend me movies based on my favourite genre
				elif len(tag_list)>1:
					response_text = "Here are your recommended movies from your Favourite Genre. "
					output = self.process_tag_recommendation(tag_list)
					if output == "":
						response["response_text"] = "Sorry we couldn't find any movie recommendations for your Favourite genre. Please add more genres that you like to your profile. "
						response["response_status"] = 0
					else:
						response["response_text"] = response_text + output
						response["response_status"] = 1

					response['response_type'] = "Recommendation"
					return response

				# Recommend me movies based on my movie history
				elif len(movie_history_list)>1:
					response_text = "Here are your recommended movies from your Movie history records. "
					output = self.process_movie_history_recommendation(movie_history_list)
					if output == "":
						response["response_text"] = "Sorry we couldn't find any movie recommendations for your movie history. Please add more movies that you like to your profile. "
						response["response_status"] = 0
					else:
						response["response_text"] = response_text + output
						response["response_status"] = 1

					response['response_type'] = "Recommendation"
					return response
				# Recommend me a movie
				else:
					print "Inside popular movies!!"
					response_text = "I couldn't find your preference. Here are some popular movies that you could watch. "
					output = self.process_popular_movies()
					if output == "":
						response["response_text"] = "Sorry we couldn't find any movies at the moment."
						response["response_status"] = 0
					else:
						response["response_text"] = response_text + output
						response["response_status"] = 1

					response['response_type'] = "Recommendation"
					return response
			else:
				continue

		# To ask generic information about the movie
		# Sample Request: Tell me about movie Avatar
		pat1 = re.compile(r'((?<=about )(.*?)(?= movie))')
		pat2 = re.compile(r'(?<=movie ).*$')
		res1 = re.search(pat1,request)
		res2 = re.search(pat2,request)
		if res1 == None and res2 == None:
			response_status = 0
			response_text = "Sorry I couldn't find the movie. Please try again."

		elif res2 == None:
			movie = res1.group()
			response_text, response_status = self.get_details(movie)

		else:
			movie = res2.group()
			response_text, response_status = self.get_details(movie)

		response["response_type"] = "Information"
		response["response_text"] = response_text
		response["response_status"] = response_status
		return response

'''
# Unit tests
movie_history_list = ["Tomorrowland (2015)","You Only Live Twice (1967)","Southland Tales (2006)","Money Train (1995)","Four Rooms (1995)"]
tag_list = ["stand up comedy","interracial romance","mad scientist","space travel"]
twitter_username = "nivedithapb"
app = MovieRecommender()
#app.process_twitter_recommendation(twitter_username)
#app.process_movie_history_recommendation(movie_history_list)
#app.process_tag_recommendation(tag_list)
response = {}
response = app.get_movies("recommend me a movie",username="", tag_list=tag_list)
print("Results obtained :\n")
print(response["response_text"])
'''
