#!/usr/bin/env python
from mechanize import Browser
from BeautifulSoup import BeautifulSoup

mech = Browser()
url = "http://www.zyxware.com/articles/4344/list-of-fortune-500-companies-and-their-websites" # originally from: http://www.biggestuscities.com/top-1000
page = mech.open(url)

html = page.read()
soup = BeautifulSoup(html)
table = soup.find("table", 'data-table')

cities = ""

for row in table.findAll('tr')[1:400]:
    col = row.findAll('td')
    city = col[1].text.split('\n')[0]
    cities = cities + city + '|'
    print cities
