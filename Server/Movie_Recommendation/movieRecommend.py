import re
import time
import math
from random import shuffle
#import queue
import Queue as queue
import pymongo
import threading
from DataService import Mongo
from TwitterService import Tweepy
from TweetAnalytics import TextAnalytics

# Recommender based on MovieLens/Genome database and Twitter profile
# db name: movieRecommend

class MovieRecommend(object):

    @classmethod
    def __init__(self, mongo):
        self.mongo = mongo
        self.db = mongo.client["movieRecommend"]
        self.db_integration = mongo.client["integration"]
        self.textAnalytics = TextAnalytics(mongo)

    @classmethod
    def get_titles_by_mids(self, mids):
        titles = []
        for mid in mids:
            movie = self.db["movie"].find_one({"mid": mid})
            if "title_full" in movie:
                titles.append(movie["title_full"])
            elif "title" in movie:
                 titles.append(movie["title"])
        return titles

    @classmethod
    def get_imdbids_by_mids(self, mids):
        imdbids = []
        for mid in mids:
            cur_movie = self.db["movie"].find_one({"mid": mid})
            cur_imdbid_len = len(str(cur_movie["imdbid"]))
            # Construct the real imdbid
            cur_imdbid = "tt"
            for i in range(7 - cur_imdbid_len):
                cur_imdbid += "0"
            cur_imdbid += str(cur_movie["imdbid"])
            imdbids.append(cur_imdbid)
        return imdbids

    @classmethod
    def get_actors_from_profile(self, profile, integrated=False):
        # get all actors from database
        actors_pool = set()
        if not integrated:
            cursor = self.db["actors_list"].find({})
            for cur_actor in cursor:
                cur_name = cur_actor["actor"]
                actors_pool.add(cur_name)
        else:
            cursor = self.db_integration["peoples_name_only"].find({})
            for cur_doc in cursor:
                for cur_name in cur_doc["names"]:
                    actors_pool.add(cur_name)
        print("[MovieRecommend] Built up actors pool, size: " + str(len(actors_pool)))

        # gain all mentioned actors and the frequency
        mentioned_actors = {}
        for user in profile["extracted_users"]:
            if user[1] in actors_pool:
                # print(user[1].encode("utf8"))
                if user[1] not in mentioned_actors:
                    mentioned_actors[user[1]] = 1
                else:
                    mentioned_actors[user[1]] += 1

        print("[MovieRecommend] Found " + str(len(mentioned_actors)) + " actors from profile.")
        # print(mentioned_actors)
        return mentioned_actors

    @classmethod
    def get_tags_from_hashtags(self, profile, tags_pool):
        # gain all mentioned tags and the frequency
        mentioned_tags = {}
        for hashtag in profile["extracted_tags"]:
            # print(hashtag.encode("utf8"))
            words = self.textAnalytics.get_words_from_hashtag(hashtag)
            for word in words:
                if word in tags_pool:
                    if word not in mentioned_tags:
                        mentioned_tags[word] = 1
                    else:
                        mentioned_tags[word] += 1

        print("[MovieRecommend] Found " + str(len(mentioned_tags)) + " tags from hashtags.")
        return mentioned_tags

    @classmethod
    def get_tags_from_tweets(self, profile, tags_pool):
        # gain all mentioned tags and the frequency
        mentioned_tags = {}
        for tweet in profile["extracted_tweets"]:
            # print(tweet.encode("utf8"))
            words = self.textAnalytics.get_words_from_tweet(tweet)
            for word in words:
                if word in tags_pool:
                    if word not in mentioned_tags:
                        mentioned_tags[word] = 1
                    else:
                        mentioned_tags[word] += 1

        print("[MovieRecommend] Found " + str(len(mentioned_tags)) + " tags from tweets.")
        return mentioned_tags

    @classmethod
    def get_tags_from_profile(self, profile, normalized=False):
        # get all tags from database
        tags_pool = set()
        if not normalized:
            cursor = self.db["tag"].find({})
            for cur_tag in cursor:
                cur_content = cur_tag["content"]
                tags_pool.add(cur_content)
        else:
            cursor = self.db_integration["normalized_tags"].find({})
            for cur_tag in cursor:
                cur_content = cur_tag["tag"]
                tags_pool.add(cur_content)
        print("[MovieRecommend] Built up tags pool, size: " + str(len(tags_pool)))

        tags_from_hashtags = self.get_tags_from_hashtags(profile, tags_pool)
        tags_from_tweets = self.get_tags_from_tweets(profile, tags_pool)

        # combine two tags dicts
        tags_dict = tags_from_hashtags
        for tag in tags_from_tweets.keys():
            if tag not in tags_dict.keys():
                tags_dict[tag] = tags_from_tweets[tag]
            else:
                tags_dict[tag] += tags_from_tweets[tag]
        print("[MovieRecommend] Found " + str(len(tags_dict)) + " tags from profile.")
        print(tags_dict)
        return tags_dict

    @classmethod
    def get_classification_from_profile(self, profile):
        classification = self.textAnalytics.get_classification(profile)
        return classification

    @classmethod
    def get_entity_from_profile(self, profile):
        entity = self.textAnalytics.get_entity(profile)
        return entity

    @classmethod
    def recommend_movies_for_twitter_integrated(self, screen_name):
        print("[MovieRecommend] Target user screen_name: " + screen_name)
        '''
        profile = self.db["user_profiles"].find_one({"screen_name": screen_name})
        if profile is None:
            print("[MovieRecommend] Profile not found in database.")
        '''
        twitter = Tweepy(self.mongo)
        profile = twitter.extract_profile(screen_name)
        print ("prifile is ", profile)
        if len(profile) == 0:
            return []

        print("[MovieRecommend] Profile retrieved.")
        actors = self.get_actors_from_profile(profile, integrated=True)
        print ('actors ', actors)
        tags = self.get_tags_from_profile(profile, normalized=True)
        print ('tags ', tags)

        # Combine actors and tags to recommend
        recommends = self.recommend_movies_combined_integrated(actors, tags)
        recommendations = []
        print("[MovieRecommend] Earned recommendations for Twitter.")

        for movie in recommends:
            recommendations.append(self.preprocess(movie))

        return recommendations

    @classmethod
    def recommend_movies_combined_integrated(self, actors, tags):
        movies_score = {}

        total_movies_num = 121479   # num of movies with tags (real)
        for tag in tags.keys():
            cur_tag = self.db_integration["normalized_tags"].find_one({"tag": tag})
            cur_popularity = cur_tag["popularity"]
            cur_movies = cur_tag["movies"]
            cur_scores = cur_tag["scores"]
            for pos in range(len(cur_movies)):
                cur_movie_title = cur_movies[pos]
                cur_movie_score = cur_scores[pos]
                # consider also the frequency
                # relevance = cur_movie_score * (1 + math.log(tags[tag], 3))
                relevance = cur_movie_score * math.sqrt(tags[tag])
                score = self.weight_tf_idf(relevance, cur_popularity, total_movies_num, 3)
                if cur_movie_title not in movies_score:
                    movies_score[cur_movie_title] = score
                else:
                    movies_score[cur_movie_title] += score

        total_actors_num = 3031430
        for actor in actors.keys():
            cur_actor = self.db_integration["peoples"].find_one({"people": actor})
            cur_popularity = cur_actor["popularity"]
            cur_movies = cur_actor["movies"]
            for cur_movie in cur_movies:
                cur_movie_title = cur_movie
                # consider also the frequency
                # relevance = 1 + math.log(actors[actor], 3)
                relevance = math.sqrt(actors[actor])
                score = self.weight_tf_idf(relevance, cur_popularity, total_actors_num, 4) * 1.3
                if cur_movie_title not in movies_score:
                    movies_score[cur_movie_title] = score
                else:
                    movies_score[cur_movie_title] += score

        print("[MovieRecommend] Found " + str(len(movies_score)) + " candidate movies.")
        recommend = self.gain_top_k(movies_score, 20)
        return recommend


    @classmethod
    def recommend_movies_based_on_tags_integrated(self, tags):
        movies_score = {}

        total_movies_num = 121479
        for tag in tags:
            cur_tag = self.db_integration["normalized_tags"].find_one({"tag": tag})
            if cur_tag is None:
                continue
            cur_popularity = cur_tag["popularity"]
            cur_movies = cur_tag["movies"]
            cur_scores = cur_tag["scores"]
            for pos in range(len(cur_movies)):
                cur_movie_title = cur_movies[pos]
                cur_movie_score = cur_scores[pos]
                relevance = cur_movie_score
                score = self.weight_tf_idf(relevance, cur_popularity, total_movies_num, 2)
                if cur_movie_title not in movies_score:
                    movies_score[cur_movie_title] = score
                else:
                    movies_score[cur_movie_title] += score

        print("[MovieRecommend] Found " + str(len(movies_score)) + " candidate movies.")
        recommend = self.gain_top_k(movies_score, 20)
        return recommend

    @classmethod
    def weight_tf_idf(self, tf, df, num_docs, base):
        return tf * math.log(float(num_docs) / (df + 1), base)

    # gain top-k candidates given a dictionary storing their scores
    @classmethod
    def gain_top_k(self, candidates, k):
        candidates_pool = queue.PriorityQueue()
        for cid in candidates:
            candidates_pool.put(Candidate(cid, candidates[cid]))
            # maintain the size
            if candidates_pool.qsize() > k:
                candidates_pool.get()

        top_k = []
        while not candidates_pool.empty():
            cur_candidate = candidates_pool.get()
            top_k.append(cur_candidate.cid)
            #print("[MovieRecommend] Candidate id: " + str(cur_candidate.cid) + ", score: " + str(cur_candidate.score))
        top_k.reverse()
        return top_k

    '''
    # given a list of recommendation movie ids, print out the movies information
    @classmethod
    def print_recommend(self, recommend):
        if len(recommend) == 0:
            return
        print("[MovieRecommend] - Recommend movies: -")
        for movie_id in recommend:
            movie_data = self.db["movie"].find_one({"mid": movie_id})
            print("[MovieRecommend] imdbid: %7d, %s" % (movie_data["imdbid"],movie_data["title"].encode("utf8")))
        print("[MovieRecommend] - Recommend end. -")
    '''

    # generate up to 20 movies recommendations given a list of movie names
    # the core idea is collaborative filtering (comparing movie occurrences)
    @classmethod
    def recommend_movies_based_on_history(self, movies):
        # convert imdb titles into mids
        target_history = set()
        for movie in movies:
            cur_movie = self.db["movie"].find_one({"title": movie})
            if cur_movie is None:
                continue
            target_history.add(cur_movie["mid"])

        print("[MovieRecommend] Start retrieve similar users...")
        most_similar_users = self.get_similar_users_by_history(target_history)
        if len(most_similar_users) == 0:
            print("[MovieRecommend] Recommend failed due to insufficient history.")
            return []

        print("[MovieRecommend] Similar users retrieved.")
        print("[MovieRecommend] Start generating recommend movies...")

        movies_count = {}
        for cur_user_id in most_similar_users:
            cur_user = self.db["user_rate"].find_one({"uid": cur_user_id})
            for rating in cur_user["ratings"]:
                # if user like this movie
                if rating[1] >= 3.5:
                    # and the movie is not in target history
                    if rating[0] not in target_history:
                        # count occurrences
                        if rating[0] not in movies_count:
                            movies_count[rating[0]] = 1
                        else:
                            movies_count[rating[0]] += 1

        recommend = self.gain_top_k(movies_count, 20)
        return recommend

    @classmethod
    def preprocess(self, movie_title):
        movie_title = re.sub('[^A-Za-z ]+', '', movie_title)
        return movie_title

    @classmethod
    def recommend_movies_based_on_popularity(self):

        movie_data = self.db["movie"].find({"$and": [{"imdb_rating":{"$gt": "9.0"}}, {"imdb_rating":{"$lt": "N/A"}}]})
        movie_set = set()

        for movie in movie_data:
            movie_title = self.preprocess(movie['title'])
            movie_set.add(movie_title)
        movie_set.remove("    ")

        recommend = list(movie_set)
        shuffle(recommend)
        return recommend

    # return top-20 similar users given user history
    # the core idea is cosine similarity between user like list
    @classmethod
    def get_similar_users_by_history(self, target_like, target_id=0):
        print("[MovieRecommend] Start calculating similar users...")
        if len(target_like) < 5:
            print("[MovieRecommend] Not enough rating history: " + str(len(target_like)) + ".")
            return []
        print("[MovieRecommend] Sufficient history: " + str(len(target_like))+ ", now start calculating...")

        progressInterval = 10000  # How often should we print a progress report to the console?
        progressTotal = 247753    # Approximate number of total users
        count = 0                 # Counter for progress

        # Scan through all users in database and calculate similarity
        startTime = time.time()
        # maintain a min heap for top k candidates
        candidates = queue.PriorityQueue()
        cursor = self.db["user_rate"].find({})
        for cur_user in cursor:
            count += 1
            if count % progressInterval == 0:
                print("[MovieRecommend] %6d users processed so far. (%d%%) (%0.2fs)" % ((count, int(count * 100 / progressTotal), time.time() - startTime)))

            cur_id = cur_user["uid"]
            if cur_id == target_id:
                continue

            cur_like = set()
            for rating in cur_user["ratings"]:
                if rating[1] >= 3.5:
                    cur_like.add(rating[0])
            if len(cur_like) < 5:
                continue
            cur_similarity = self.cosine_similarity(cur_like, target_like)
            candidates.put(Candidate(cur_id, cur_similarity))
            # maintain the pool size
            if candidates.qsize() > 20:
                candidates.get()

        # now print out and return top 20 candidates
        most_similar_users = []
        while not candidates.empty():
            cur_user = candidates.get()
            most_similar_users.append(cur_user.cid)
        print("[MovieRecommend] Calculation complete (%0.2fs)" % (time.time() - startTime))
        most_similar_users.reverse()

        return most_similar_users

    @classmethod
    def cosine_similarity(self, set1, set2):
        match_count = self.count_match(set1, set2)
        return float(match_count) / math.sqrt(len(set1) * len(set2))

    @classmethod
    def count_match(self, set1, set2):
        count = 0
        for element in set1:
            if element in set2:
                count += 1
        return count

class Candidate(object):
    def __init__(self, cid, score):
        self.cid = cid
        self.score = score
    def __lt__(self, other):
        return self.score < other.score


def main():
    recommender = MovieRecommend(Mongo("movieRecommend"))

    # # -----------------------------------------------------------------

    # # unit test, input: User ID = 4
    # print("[MovieRecommend] ***** Unit test for recommend_movies_for_user() *****")
    # user_id = 4
    # recommends = recommender.recommend_movies_for_user(user_id)
    # recommender.print_recommend(recommends)

    # # -----------------------------------------------------------------

    # # unit test, input tags:
    # # [28, 387, 599, 704, 794]
    # # ["adventure", "feel-good", "life", "new york city", "police"]
    # print("[MovieRecommend] ***** Unit test for recommend_movies_based_on_tags() *****")
    # tags = [28, 387, 599, 704, 794]
    # recommends = recommender.recommend_movies_based_on_tags(tags)
    # recommender.print_recommend(recommends)

    # print("[MovieRecommend] ***** Unit test for recommend_movies_based_on_tags() with tag contents input *****")
    # tags = ["adventure", "feel-good", "life", "new york city", "police"]
    # recommends = recommender.recommend_movies_based_on_tags(tags, tagid=False)
    # recommender.print_recommend(recommends)

    # # -----------------------------------------------------------------

    # # unit test, input: Movie ID = 1 "Toy Story (1995)"
    # print("[MovieRecommend] ***** Unit test for recommend_movies_for_movie() *****")
    # movie_id = 1
    # recommends = recommender.recommend_movies_for_movie(movie_id)
    # recommender.print_recommend(recommends)

    # # -----------------------------------------------------------------

    # print("[MovieRecommend] ***** Unit test for recommend_movies_for_twitter() *****")
    # user_screen_name = "BrunoMars"
    # # user_screen_name = "LeoDiCaprio"
    # # user_screen_name = "BarackObama"
    # # user_screen_name = "sundarpichai"
    # # user_screen_name = "BillGates"
    # # user_screen_name = "jhsdfjak"
    # recommends = recommender.recommend_movies_for_twitter(user_screen_name)
    # # recommender.print_recommend(recommends)
    # print(recommender.get_titles_by_mids(recommends))

    # # -----------------------------------------------------------------

    # print("[MovieRecommend] ***** Unit test for recommend_movies_for_twitter_integrated() *****")
    # user_screen_name = "BrunoMars"
    # # user_screen_name = "LeoDiCaprio"
    # # user_screen_name = "BarackObama"
    # # user_screen_name = "sundarpichai"
    # # user_screen_name = "BillGates"
    # # user_screen_name = "jhsdfjak"
    # recommends = recommender.recommend_movies_for_twitter_integrated(user_screen_name)
    # for recommend in recommends:
    #     print(recommend.encode("utf8"))

    # # -----------------------------------------------------------------

    # # unit test, input tags:
    # # ["adventure", "feel good", "life", "new york city", "police"]
    # print("[MovieRecommend] ***** Unit test for recommend_movies_based_on_tags_integrated() with tag contents input *****")
    # tags = ["adventure", "feel good", "life", "new york city", "police"]
    # recommends = recommender.recommend_movies_based_on_tags_integrated(tags)
    # for recommend in recommends:
    #     print(recommend.encode("utf8"))

    # # -----------------------------------------------------------------

    # unit test for recommend_movies_based_on_history()
    print("[MovieRecommend] ***** Unit test for recommend_movies_based_on_history() *****")
    user_history = []
    user_history.append("Toy Story (1995)")
    user_history.append("Big Hero 6 (2014)")
    user_history.append("X-Men: Days of Future Past (2014)")
    user_history.append("The Lego Movie (2014)")
    user_history.append("The Secret Life of Walter Mitty (2013)")
    user_history.append("Death Note: Desu nto (2006)")
    user_history.append("Zombieland (2009)")
    user_history.append("Fifty Shades of Grey (2015)")
    user_history.append("The Maze Runner (2014)")

    recommends = recommender.recommend_movies_based_on_history(user_history)
    recommends = recommender.get_titles_by_mids(recommends)
    for recommend in recommends:
        print(recommend.encode("utf8"))

if __name__ == "__main__":
    main()
