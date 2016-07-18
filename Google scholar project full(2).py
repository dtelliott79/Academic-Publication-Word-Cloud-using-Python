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
    searchstring = '.*user='+str(user)[2:len(str(user))-2]+'.*'+'&citation_for_view='+str(user)[2:len(str(user))-2]+'.*'

    PUBlink = re.findall(searchstring, link)																	#Regular expression above creates a string of "user=***Google Scholar user id***&citation_for_view=***Google Scholar user id***", 
    if len(PUBlink) > 0:																			#characteristic to each publication citations on Google Scholar profile page.
        PUBlinks.append(PUBlink)																			#For those urls that match the format of publication citations, pull out and save as elements in a list.

######################################################################################################################################################################
### The code below takes each Google Scholar citation page, parses the HTML, and extracts urls for external link to follow, one for each publication, 
### leading either to the fUll-text PDF, the fUll-text HTML, or the main page HTML with abstract (in that order of preference by availability).
######################################################################################################################################################################

EXTERNALlinks = []																				#Create empty list used to store external publication fulltexts or publisher website citations.

for link in PUBlinks:																				#Loop through all urls in list of publication citations.

    url = 'https://scholar.google.com'+str(link)[3:len(str(link))-2]			
    html = urllib.urlopen(url).read()																		#Open each citation url with urllib.
    soup = BeautifulSoup(html)																			#Parse html from each citation url with BeautifulSoup.
###    soup = BeautifulSoup(open('filename.html'))																#reading from local file for practice

    tags = soup('a')																				#Retrieve all anchor tags from parsed HTML and save as list.

    MAINlink = ''
    FULLTEXTlink = ''
    for tag in tags:																				#Loop through all anchor tags on each publication citation page.
        if len(FULLTEXTlink) > 0: break
        span = tag.findAll('span')
        for each_tag in span:																			#Look for those matching a PDF or HTML fulltext link, with class ('gsc_title_ggt') in the child 'span' tag.
            if each_tag['class'] == 'gsc_title_ggt':
                FULLTEXTlink = tag.get('href', None)
                break

        if tag.get('class') == 'gsc_title_link':																#Look for those matching a publishers main citation link, with class ('gsc_title_link').
            MAINlink = tag.get('href', None)

        if len(FULLTEXTlink) > 0:																		#Once the fulltext link is found, append it to the list of EXTERNALlinks and exit the loop for that publication.
            EXTERNALlinks.append(FULLTEXTlink)
            break

        if len(MAINlink) > 0:																			#If the fulltext link is not found, append the publisher website citation to the list of EXTERNALlinks and exit the loop for that publication.
            EXTERNALlinks.append(MAINlink)
            break
    time.sleep(5)

######################################################################################################################################################################
### The code below loops through the urls for external links to follow for each publication. For each, it first determines if the url links to a PDF or HTML,
### parses the fUll-text file (or abstract if full-text is not open-access), splits each line in the readable text into words, and 
### keeps a count of the number of occurrences of each word in a dictionary (d). 
######################################################################################################################################################################

d = {}																						#Create the dictionary to store words counts in.
trans = {}																					#Create the dictionary to store words for each stem in.
loops = 0
fail = []																					#Counter to make sure program goes through every EXTERNALlink/publication.

from urllib2 import Request, urlopen
from PyPDF2 import PdfFileWriter, PdfFileReader
from StringIO import StringIO


for link in EXTERNALlinks:																			#Loops through each EXTERNALlink to fulltext publications or publisher's main page.
    loops = loops + 1
    try:
        fhand = urllib.urlopen(link)																		#Opens each EXTERNALlink and pulls out information on filetype (PDF or HTML).
        http_message = fhand.info()
        full = http_message.type
    except:																					#Guards against an invalid or blocked url/file.
        continue
###    print full

    if 'pdf' in full:																				#For PDF filetypes, opens and parses PDF.
        remoteFile = urlopen(Request(link)).read()
	###remoteFile = open('filename.pdf', 'rb').read()															#Open local PDF for practice.
###        print link
###        print len(remoteFile)
        if not len(remoteFile) > 25000:
            fail.append(link)
        memoryFile = StringIO(remoteFile)
        pdfFile = PdfFileReader(memoryFile)

        text = ''

        for iter in range(pdfFile.numPages):																	#Extracts PDF text and splits into component words (all lowercase).
            pageObj = pdfFile.getPage(iter)
            text = pageObj.extractText()
            text = text.strip().lower()
            words = text.split()
            for word in words:																			#For each word identified, strips down to bare text, removes digits and puncutation, guards against problems (unusual formats that would cause an error, as well as unusually long word resulting from concatenation of multiple words, both potential problems when parsing a PDF), and keeps a count of how many times each word occurrs in the dictionary (d).
                try:
                    word = str(word).strip().translate(None, string.digits).translate(None, string.punctuation).replace('\n', '')
                except:
                    continue
                if len(word) > 20: continue

                d[word] = d.get(word,0) + 1


    if 'html' in full:
        soup = BeautifulSoup(fhand)																		#For HTML filetypes, parses html with BeautifulSoup.
        ###soup = BeautifulSoup(open("filename.html"))																#Open local HTML fulltext for practice.
        texts = soup.findAll(text=True)																		#Within parsed HTML, finds and extracts only visible text.
        def visible(element):
            if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
                return False
            elif re.match('<!--.*-->', str(element)):
                return False
            return True
        visible_texts = filter(visible, texts)
###        print link
###        print len(visible_texts)
        if not len(visible_texts) > 25:
            fail.append(link)
        for text in visible_texts:																		#Splits extracted text into component words (all lowercase).
            text = str(text).strip().lower()
            words = text.split()
            for word in words:																			#For each word identified, strips down to bare text, removes digits and puncutation, guards against problems (unusual formats that would cause an error, as well as unusually long word resulting from concatenation of multiple words), and keeps a count of how many times each word occurrs in the dictionary (d).
                try:
                    word = str(word).strip().translate(None, string.digits).translate(None, string.punctuation).replace('\n', '')
                except:
                    continue
                if len(word) > 20: continue

                d[word] = d.get(word,0) + 1

for link in fail:
    while True:
        print 'Parsing of the fulltext at the following url appears to have failed:'
        print link
        print 'Do you want to manually enter a local filename for this publication?'
        local = raw_input('(y or n)? ')
        if local == 'n': 
            break
        elif local == 'y':
            localfile = raw_input('Please enter the filename of the full-text pdf you want to read in (Note that it must be saved in the same directory as this program, and must include the file type suffix ".pdf"): ')
            try:
                remoteFile = open((localfile), 'rb').read()
                memoryFile = StringIO(remoteFile)
                pdfFile = PdfFileReader(memoryFile)

                text = ''

                for iter in range(pdfFile.numPages):																	#Extracts PDF text and splits into component words (all lowercase).
                    pageObj = pdfFile.getPage(iter)
                    text = pageObj.extractText()
                    text = text.strip().lower()
                    words = text.split()
                    for word in words:																			#For each word identified, strips down to bare text, removes digits and puncutation, guards against problems (unusual formats that would cause an error, as well as unusually long word resulting from concatenation of multiple words, both potential problems when parsing a PDF), and keeps a count of how many times each word occurrs in the dictionary (d).
                        try:
                            word = str(word).strip().translate(None, string.digits).translate(None, string.punctuation).replace('\n', '')
                        except:
                            continue
                        if len(word) > 20: continue

                        d[word] = d.get(word,0) + 1
            except:
                print 'Error.', localfile, 'is not a valid filename for a pdf to read in.'
                continue 
            break
        else:
            print 'Error:', local, 'is not a valid response.'
            continue
            
######################################################################################################################################################################
### The code below is a sub-program that extracts the 100 most common words from an HTML based table on Wikipedia and 
### combines them with another, user-defined, list of words to exclude from the word cloud (mostly scientific jargon in my case).
######################################################################################################################################################################

url = 'https://en.wikipedia.org/wiki/Most_common_words_in_English'
html = urllib.urlopen(url).read()
soup = BeautifulSoup(html)
commonwords = list()

tags = soup('td')
for tag in tags:
    value = re.findall('.*<td>(.+)</td>.*', str(tag))
    if str(value)[2:10] == '<a href=':
        value = re.findall('.*>(.+)<.*', str(value))
    value = str(value).strip().translate(None, string.digits).translate(None, string.punctuation)
    if len(str(value)) == 0: continue
    if len(str(value)) > 16: continue
    commonwords.append(str(value))

jargon = [] #['the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'I', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', '', 'speci', 'neutral', 'crossref', 'scholar', 'second', 'species', 'fig\xe2', 'k', 'united', 'river', 'rivers', 'nutrients', 'nutrient', 'adults', 'adult', 'sedimentation', 'sediment', 'layers', 'layer', 'lations', 'variety', 'various', 'l', 'meaning', 'devreker', 'oceanogr', 'eutrophic', 'eutrophication', 'journal', 'journals', 'carcasses', 'carcass', 'antarctica', 'photosynthetic', 'photosynthetically', 'incubation', 'incubated', 'incuba', 'incubations', 'mesozooplankton', 'tion', 'tions', 'thus', 'estuaries', 'estuar', 'estuary', 'hatched', 'hatch', 'hatching', 'marine', 'dois', 'doi', 'm', 'de', 'coast', 'coastal', 'coasts', 'bays', 'bay', 'habitat', 'habitats', 'habits', 'wo', 'wk', 'carboy', 'carboys', 'carbon', 'cope', 'copy', 'however', 'underice', 'free', 'three', 'been', 'much', 'dry', 'identi', 'tang', 'concentrated', 'concentrations', 'cont', 'concentration', 'mexico', 'is', 'ii', 'iis', 'iii', 'im', 'ice', 'ices', 'ide', 'ngomex', 'zooplankton', 'similis', 'quantum', 'publishing', 'publications', 'publish', 'public', 'publisher', 'published', 'publication', 'publishers', 'eprs', 'epr', 'salinity', 'salinities', 'dead', '\xe2\x80\xaa\xe2\x80\xaa', 'hypoxic', 'hypoxia', 'o', 'january', 'was', 'pest', 'abstract', 'california', 'where', 'wher', 'tester', 'bottom', 'roman', 'royer', 'royal', 'table\xe2', 'taxonomic', 'mg', 'ecol', 'signi', 'signed', 'v', 'helicina', 'nonpredatory', 'nonpr', 'predatory', 'predators', 'pred', 'predator', 'predation', 'university', 'black', 'northern', 'greenbug', 'greenbugs', 'car', 'care', 'career', 'mar', 'matte', 'matter', 'materials', 'material', 'mates', 'southern', 'pteropod', 'pteropods', 'such', 'grower', 'growers', 'manner', 'managers', 'manager', 'manage', 'management', 'managing', 'sp', 'kimmel', 'hirstag', 'hirst', 'thanks', 'thank', 'window', 'windows', 'somatic', 'discussion', 'discussed', 'discuss', 'north', 'trophic', 'pierson', 'edatory', 'ed', 'eded', 'eds', 'eg', 'egg', 'eggs', 'copepod', 'copepods', 'copepoda', 'g', 'biol', 'crit', 'qual', 'serv', 'waters', 'water', 'recruitment', 'recruited', 'series', 'chlorophyll', 'san', 'zone', 'zones', 'environmental', 'environ', 'environment', 'environments', 'survivors', 'survival', 'survive', 'survived', 'survivable', 'gulf', 'stained', 'stain', 'staining', 'genus', 'generally', 'generations', 'reviewers', 'reviewed', 'review', 'between', 'jr', 'lopez', 'prosome', 's', 'colonies', 'colony', 'populations', 'poppe', 'polar', 'colonize', 'colonized', 'colonization', 'colonial', 'poc', 'marcus', 'sound', 'oklahoma', 'animals', 'animal', 'proteins', 'protein', 'aphid', 'aphids', 'ecological', 'ecology', 'cell', 'cells', 'being', 'lethal', 'leth', 'ross', 'mor', 'intact', 'freezing', 'austral', 'australian', 'article', 'articles', 'oceans', 'oceanic', 'oc', 'oce', 'ocean', 'acta', 'open', 'opmental', 'opp', 'op', 'starvation', 'starved', 'bottles', 'bottle', 'e', 'age', 'ag', 'ageing', 'agency', 'al', 'ality', 'alive', 'deeper', 'deep', 'ar', 'arr', 'are', 'google', 'fields', 'field', 'organism', 'organisms', 'organization', 'organic', 'sci', 'choptank', 'chesapeake', 'adapted', 'adaptations', 'adaptation', 'vertical', 'vertically', '\xe2\x88\x92', 'calanoida', 'calanoides', 'calanoid', 'diet', 'dietary', 'diets', 'hyp', 'biology', 'biological', 'biologie', 'able', 'ability', 'oxygenated', 'oxygen', 'vital', 'small', 'mort', 'mortalities', 'mortal', 'morta', 'morten', 'mortality', '\xe2\x86\xb5', 'depth', 'ft', 'bloom', 'blooms', 'section', 'smith', 'help', 'economic', 'through', 'nauplii', 'nauplius', 'naupliar', 'vlt', 'food', 'oxford', 'fisher', 'fishes', 'fish', 'copepodites', 'copepodite', 'oceanography', 'oceanographic', 'limnology', 'fig\xe2\xa0', 'w', 'parts', 'part', 'dissolution', 'dissolved', 'life', 'literature', 'literat', 'live', 'living', 'pubmedncbi', 'clearance', 'huntley', 'ext', 'kw', 'find', 'access', 'accessible', 'b', 'pellets', 'pellet', 'cruises', 'cruise', 'ser', 'sea', 'seaice', 'web', 'webs', 'both', 'c', 'those', 'elliott', 'dur', 'pantarctica', 'solid', 'therefore', 'solitary', 'full', 'fully', 'alert', 'alerts', 'alerting', 'dark', 'darkness', 'amp', 'current', 'currents', 'limnol', 'd', 'fluxes', 'bacterivorous', 'bacterial', 'bacter', 'openurl', 'perature', 'behavioral', 'behavior', 'prog', 'reproduction', 'reproductive', 'reproduced', 'reproduce', 'aquat', 'aquatic', 'bacteria', 'decomposition', 'phaeocystis', 'usa', 'citing', 'cited', 'citation', 'z', 'great', 'nature', 'natural', 'naturally', 'nat', 'national', 'gt', 'maryland', 'estuarine', 'biomasses', 'biomass', '\xe2\xb5', 'download', 'affinis', 'turbidity', 'turbid', 'bodies', 'body', 'bodied', 'sinking', 'sink', 'producers', 'producer', 'produced', 'production', 'produce', 'products', 'productivity', 'produc', 'slide', 'limacina', 'applications', 'feeding', 'feed', 'fecal', 'community', 'communities', 'females', 'fems', 'female', 'chl', 'spp', 'taxa', 'f', 'acartia', 'atonsa', 'proceedings', 'insecticides', 'insecticide', 'online', 'surface', 'size', 'sizes', 'light', 'issue', 'issues', 'dmsp', 'lt', 'authors', 'author', 'date', 'dation', 'days', 'edition', 'editorial', 'editor', 'editors', 'kpa', 'trapped', 'traps', 'trap', 'res', 'may', 'sublethal', 'rela', 'regional', 'register', 'regulation', 'red', 'localized', 'local', 'has', '\xe2\xb0c', 'long', 'longer', 'eurytemora', 'shelf', 'respiratory', 'respiration', 'cycles', 'cyclic', 'cycle', 'phytoplankton', 'wheat', 'density', 'text', 'microbes', 'microbial', 'microb', 'antarctic', 'particulate', 'particles', 'particle', 'grazing', 'grazers', 'graze', 'h', 'views', 'view', 'progress', 'email', 'plankton', 'planktonic', 'etms', 'etm', 'cs', 'cent', 'policies', 'policy', 'ann', 'anal', 'situ', 'i', 'often', 'mcmurdo', 'adv', 'were', 'pressures', 'pressure', 'press', 'residual', 'residence', 'residing', 'reside', 'succession', 'successful', 'success', 'successfully', 'tonsa', 'freshwater', 'avoid', 'avoiding', 'avoidance', '\xe2\x80\xaa\xee\xbcm', 'cooccurrence', 'cooccurring', 'although', 'column', 'ingest', 'ingestion', 'powerpoint', 'early', 'earth', 'earlier', 'temperatures', 'temperate', 'temperature', 'temp', 'ecosystems', 'ecosystem', 'j', 'evaluate', 'et', 'etal', 'ind', 'indi', 'diego', 'erence', 'ered', 'er', 'states', 'station', 'stations', 'state', 'stage', 'stages', '\xe2\x80\x93', 'specially', 'special', 'recovery', 'laboratory', 'lab', 'dominance', 'dominated', 'dominant', 'winter', 'measurement', 'measurements', 'measure', 'measuring', 'measures', 'measured', 'each', 'total', 'primarily', 'primary', 'reported', 'reports', 'report', 'base', 'based', 'basis', 'basic', 'assumed', 'assumes', 'assume', 'assumption', 'assuming', 'assumptions', 'near', 'nearly', 'contents', 'content', 'similarly', 'flux', 'support', 'supporting', 'supported', 'supports', 'spring', 'sources', 'source', 'appear', 'appears', 'appeared', 'appearance', 'previous', 'previously', 'presented', 'presence', 'present', 'shown', 'individuals', 'individual', 'positively', 'positive', 'positions', 'position', 'composition', 'compositions', 'importantly', 'importance', 'important', 'many', 'potentially', 'potential', 'periodically', 'periods', 'period', 'develop', 'development', 'developmental', 'developed', 'abundances', 'abundant', 'abundance', 'more', 'population', 'moderated', 'moderate', 'modified', 'modules', 'module', 'actively', 'actually', 'active', 'actual', 'action', 'activities', 'activity', 'low', 'lower', 'scientific', 'science', 'sciences', 'summer', 'sum', 'summers', 'method', 'methods', 'remained', 'remaining', 'remains', 'remain', 'foundation', 'found', 'research', 'researchers', 'partial', 'partially', 'severity', 'severe', 'experienced', 'duration', 'during', 'durations', 'within', 'next', 'inclusion', 'including', 'included', 'include', 'usually', 'using', 'used', 'uses', 'user', 'useful', 'useable', 'represents', 'representative', 'represent', 'represented', 'representation', 'treatments', 'treatment', 'treat', 'treated', 'treating', 'applied', 'applies', 'application', 'apply', 'applying', 'accounting', 'accounted', 'account', 'refer', 'reference', 'references', 'determines', 'determined', 'determination', 'determining', 'determinations', 'determine', 'fact', 'facts', 'contributed', 'limits', 'limitations', 'limit', 'limited', 'limitation', 'limiting', 'direction', 'direct', 'calculator', 'line', 'lines', 'likely', 'experience', 'experiences', 'due', 'collections', 'collecting', 'collected', 'collection', 'collect', 'large', 'largely', 'larger', 'high', 'highly', 'higher', 'net', 'nets', 'end', 'late', 'later', 'livedead', 'provided', 'provide', 'providing', 'provides', 'suggesting', 'suggested', 'suggest', 'suggests', 'occurs', 'occur', 'under', 'similar', 'levels', 'level', 'sign', 'signs', 'should', 'occurring', 'occurrence', 'occurred', 'required', 'requires', 'requirements', 'require', 'requirement', 'initial', 'initially', 'tows', 'tow', 'towing', 'commonly', 'common', 'several', 'experiments', 'experimental', 'experiment', 'samplings', 'sampled', 'sample', 'sampling', 'samples', 'perate', 'greatly', 'greater', 'process', 'processing', 'processes', 'taken', 'regions', 'region', 'system', 'systems', 'contributing', 'contribute', 'contribution', 'contributions', 'addition', 'additional', 'less', 'estimate', 'estimates', 'estimated', 'estimating', 'possible', 'approximately', 'area', 'specific', 'preserve', 'ml', 'verti', 'vertical', 'exp', 'ad', 'acid', 'codend', 'observa', 'indian', 'efficiency', 'area', 'areas', 'approximately', 'handling', 'among']

ignore = jargon + commonwords

######################################################################################################################################################################
### The code below takes the dictionary of word counts (d), creates a second dictionary (d2) of only word stems (combining related words).
### It allows the user to control how many word stems are included in results, and what words are included under each word stem.
### Finally, it creates a list of tuples of occurrence, word (excluding ignored), and sorts that list by most common word.
######################################################################################################################################################################

from nltk.stem.lancaster import LancasterStemmer

while True:
    L = list()
    d2 = {}
    trans = {}

    for key, val in d.items():
        if val < 2: continue																			#Weeds out words that are single occurence, including many nonsensical artifacts of parsing the PDFs
        if key in ignore: continue
        try:
            stemword = LancasterStemmer().stem(key)
        except: continue
        if stemword in trans:
            trans[stemword].append(str(key))
        else:
            try: 
                trans[stemword] = [str(key)]
            except: continue
        d2[stemword] = d2.get(stemword,0) + val

    print 'The program found and extracted', sum(d.itervalues()), 'words of interest from', loops, 'publications. A total of', len(d2), 'distinct word stems were found.'

    while True:
        thres = raw_input('Please enter the minimum number of occurrences for which a word stem should be considered in results: ')
        try:
            thres = float(thres)
        except:
            print 'Error:', thres, 'is not a valid integer number.'
            continue
        if type(thres) == float and thres > 0: break
        else:
            print 'Error:', thres, 'is not a valid positive number.'
            continue

    while True: 
        manual = raw_input('Do you want to manually select words to include under each word stem? (y or n): ')
        if manual == 'y': break
        elif manual == 'n': break
        else:
            print 'Error:', manual, 'is not a valid response.'
            continue

    if manual == 'y':
        for key, val in trans.items():
            if d2[key] < thres: continue
            for v in val:
                print 'Do you want to keep the following word stem - word pairing:'
                print key, '-', v
                while True:
                    incl = raw_input('(y or n)? (To accept all remaining and exit, type "exit"): ')
                    if incl == 'n': 
                        ignore.append(v)
                        break
                    elif incl == 'y' or incl =='exit': 
                        break
                    else:
                        print 'Error:', incl, 'is not a valid response.'
                        continue
                if incl == 'exit': break
            if incl == 'exit': break

    if manual == 'n': break

for key, val in d2.items():
    try:
        if val < thres: continue
        key = str(key)
        if len(key) == 0: continue
        variants = trans[key]
        root = (min((variants), key=len))
        L.append((val, root))
    except:
        continue

L.sort(reverse=True)

######################################################################################################################################################################
### The code below creates another list of only the top X words (user-defined). It then creates a word cloud from this last list, 
### as well as a bar graph of the 10 most common words from the word cloud.
######################################################################################################################################################################

while True:
    X = raw_input('Please enter the maximum number of words you would like in your word cloud: ')
    try:
        X = int(X)
    except:
        print 'Error:', X, 'is not a valid integer number.'
        continue
    if type(X) == int and X > 0: break
    else:
        print 'Error:', X, 'is not a valid positive number.'
        continue

TopWords = L[:X]

count = 0
for l in TopWords:
    word = l[1]
    occur = l[0]
    if word == 'fig':
        word = 'figure'
    if word == 'p':
        word = 'p-value'
    if word == 't':
        word = 't-test'
    if word == 'maxima':
        word = 'maximum'
    if word == 'r':
        word = 'r-coefficient'
    if word == 'n':
        word = 'sample-size'
    if word == 'eq':
        word = 'equation'
    if word == 'aver':
        word = 'average'
    if word == 'x':
        word = 'x-variable'
    if word == 'y':
        word = 'y-variable'
    TopWords[count] = (word, occur)
    count = count + 1

TopTen = TopWords[:10]

from pytagcloud import create_tag_image, make_tags

tags = make_tags(TopWords, maxsize=120)
create_tag_image(tags, 'cloud_large.png', size=(1000,1000), background=(0, 0, 0, 255), fontname='Lobster', rectangular=True)
import webbrowser
webbrowser.open('cloud_large.png')

import numpy as np
import matplotlib.pyplot as plt

words = zip(*TopTen)[0]
occurences = zip(*TopTen)[1]
x_pos = np.arange(len(words))

plt.bar(x_pos, occurences, align='center')
plt.xticks(x_pos, words)
plt.ylabel('Number of Occurrences')
plt.show()
