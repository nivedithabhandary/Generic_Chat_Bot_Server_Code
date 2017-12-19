import re
train_file = "train.dat"

def combine(filename, label):
    with open(filename, "r") as fh:
        lines = fh.readlines()

    target = open(train_file, 'a')
    for line in lines:
        new_line  = label + line
        target.write(new_line)
    target.close()

def get_movies(filename):
    with open(filename, "r") as fh:
        lines = fh.readlines()
    movie_names = []
    for line in lines:
        name = line[5:]
        name = name.replace("\n","")
        movie_names.append(name)
    return " | ".join(str(movie) for movie in movie_names)

def get_from_other_files(filename):
    f = open(filename,'r')
    lines = f.readlines()
    print lines[10]
    target = open(train_file, 'a')
    for line in lines:
        target.write(line)
    target.close()

combine("weather_data.txt", "Weather ")
combine("movie_data.txt", "Movie ")
combine("music_data.txt", "Music ")
combine("news_data.txt", "News ")
combine("food_data.txt", "Food ")

combine("time_data.txt", "Time ")
combine("metadata_data.txt", "Metadata ")
combine("places_data.txt", "Places ")
combine("fallback_data.txt", "Fallback ")
combine("alexa_fallback.txt","Fallback ")

get_from_other_files("math.txt")
#get_from_other_files("fallout.txt")

#print get_movies("movie_names.txt")
