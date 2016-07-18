import re
import urllib
from BeautifulSoup import *
import PyPDF2
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time

######################################################################################################################################################################
### The code below takes a user's Google Scholar profile page, parses the HTML, and extracts links to each Google Scholar citation page for that user's 
### publications. It may need to be tweaked for users that have more than 20 publications, as the first 20 are all that are displayed by default.
######################################################################################################################################################################

while True:
    url = raw_input('Please enter the address for your Google Scholar profile: ')												#User enters their Scholar profile url of interest
    driver = webdriver.Chrome()
    try:
        driver.get(url)
        gsc_bpf_more = driver.find_element_by_id("gsc_bpf_more").click()
        # Wait *up to* 20 seconds to make sure the page has finished loading (check that the button no longer exists)
        WebDriverWait(driver,20).until(EC.invisibility_of_element_located((By.LINK_TEXT, "Show more")))
        time.sleep(5)
        # Get the html
        html = driver.page_source
        break
    except:
        print 'Error:', url, 'is not a valid Google Scholar profile address.'													#Guards against an invalid url entry.
        continue

user = re.findall('.*user=(\S+)&.*', url)																	#Regular expression to extract Google Scholar user id from url.
soup = BeautifulSoup(html)																			#Parse html from starting url with BeautifulSoup.
###soup = BeautifulSoup(open('filename.html'))																	#reading from local file for practice

tags = soup('a')																				#Retrieve all anchor tags from parsed HTML and save as list.
PUBlinks = []																					#Create empty list used to store the publication citations on Google Scholar profile page.

for tag in tags: 																				#Loop through all anchor tags and pull out href attributes into a list.
    link = tag.get('href', None)
    print link
    searchstring = '.*user='+str(user)[2:len(str(user))-2]+'.*'+'&citation_for_view='+str(user)[2:len(str(user))-2]+'.*'

    PUBlink = re.findall(searchstring, link)																	#Regular expression above creates a string of "user=***Google Scholar user id***&citation_for_view=***Google Scholar user id***", 
    if len(PUBlink) > 0:																			#characteristic to each publication citations on Google Scholar profile page.
        PUBlinks.append(PUBlink)																		#For those urls that match the format of publication citations, pull out and save as elements in a list.

print len(PUBlinks)
