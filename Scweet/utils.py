import re
import csv
import os
from time import sleep
#from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import datetime
import argparse
from msedge.selenium_tools import Edge, EdgeOptions
import pandas as pd
import platform
#from selenium.webdriver.common.keys import Keys




def get_data(card):
    """Extract data from tweet card"""
    try:
        username = card.find_element_by_xpath('.//span').text
    except :
        return

    try:
        handle = card.find_element_by_xpath('.//span[contains(text(), "@")]').text
    except :
        return

    try:
        postdate = card.find_element_by_xpath('.//time').get_attribute('datetime')
    except :
        return

    try:
        comment = card.find_element_by_xpath('.//div[2]/div[2]/div[1]').text
    except :
        comment = ""

    try:
        responding = card.find_element_by_xpath('.//div[2]/div[2]/div[2]').text
    except :
        responding = ""
    
    text = comment + responding
    
    try:
        reply_cnt = card.find_element_by_xpath('.//div[@data-testid="reply"]').text
    except :
        reply_cnt= 0

    try:
        retweet_cnt = card.find_element_by_xpath('.//div[@data-testid="retweet"]').text
    except :
        retweet_cnt = 0

    try:
        like_cnt = card.find_element_by_xpath('.//div[@data-testid="like"]').text
    except :
        like_cnt = 0

    try:
    	element = card.find_element_by_xpath('.//div[2]/div[2]//img[contains(@src, "twimg")]')
    	image_link = element.get_attribute('src') 
    except:
        image_link = ""
        
   	#handle promoted tweets
    try:
        promoted = card.find_element_by_xpath('.//div[2]/div[2]/[last()]//span').text == "Promoted"
    except:
        promoted = False
    if promoted:
    	return

    # get a string of all emojis contained in the tweet
    try:
        emoji_tags = card.find_elements_by_xpath('.//img[contains(@src, "emoji")]')
    except : 
        return
    emoji_list = []
    for tag in emoji_tags:
        try:
            filename = tag.get_attribute('src') 
            emoji = chr(int(re.search(r'svg\/([a-z0-9]+)\.svg', filename).group(1), base=16))
        except AttributeError:
            continue
        if emoji:
            emoji_list.append(emoji)
    emojis = ' '.join(emoji_list)

    #tweet url
    try:
    	element = card.find_element_by_xpath('.//a[contains(@href, "/status/")]')
    	tweet_url = element.get_attribute('href') 
    except:
    	return
    
    tweet = (username, handle, postdate, text, emojis, reply_cnt, retweet_cnt, like_cnt, image_link, tweet_url)
    return tweet  



def init_driver(navig="chrome", headless=True, proxy=None):
    # create instance of web driver
    if navig == "chrome":
        browser_path = ''
        if platform.system() == 'Windows':
            print('Detected OS : Windows')
            browser_path = './drivers/chromedriver_win.exe'
        elif platform.system() == 'Linux':
            print('Detected OS : Linux')
            browser_path = './drivers/chromedriver_linux'
        elif platform.system() == 'Darwin':
            print('Detected OS : Mac')
            browser_path = './drivers/chromedriver_mac'
        else:
            raise OSError('Unknown OS Type')    
        options = Options()
        if headless is True:
        	print("Scraping on headless mode.")
        	options.add_argument('--disable-gpu')
        	options.headless=True
        else:
        	options.headless=False
        options.add_argument('log-level=3')
        if proxy!=None:
        	options.add_argument('--proxy-server=%s' % proxy)
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(options=options,executable_path=browser_path)
        driver.set_page_load_timeout(100)
        return driver
    elif navig == "edge":
        browser_path = 'drivers/msedgedriver.exe'
        options = EdgeOptions()
        if proxy!=None:
        	options.add_argument('--proxy-server=%s' % proxy)
        if headless==True:
        	options.headless = True
        	options.use_chromium = False
        else:
        	options.headless = False
        	options.use_chromium = True
        options.add_argument('log-level=3')
        driver = Edge(options=options, executable_path=browser_path)
        return driver

def log_search_page(driver, start_date, end_date, lang, display_type, words, to_account, from_account):

    ''' Search for this query between start_date and end_date'''

    #req='%20OR%20'.join(words)
    if from_account!=None:
    	from_account = "(from%3A"+from_account+")%20"
    else :
    	from_account=""

    if to_account!=None:
    	to_account = "(to%3A"+to_account+")%20"
    else:
    	to_account=""

    if words!=None:
    	words = str(words).split("//")
    	words = "("+str('%20OR%20'.join(words))+")%20"
    else : 
    	words=""

    if lang!=None:
    	lang = 'lang%3A'+lang
    else : 
    	lang=""
    	
    end_date = "until%3A"+end_date+"%20"
    start_date = "since%3A"+start_date+"%20"

    #to_from = str('%20'.join([from_account,to_account]))+"%20"

    driver.get('https://twitter.com/search?q='+words+from_account+to_account+end_date+start_date+lang+'&src=typed_query')
    
    sleep(1)

    # navigate to historical 'Top' or 'Latest' tab
    try:
        driver.find_element_by_link_text(display_type).click()
    except:
        print("Latest Button doesnt exist.")

        
def get_last_date_from_csv(path):

	df = pd.read_csv(path)
	return datetime.datetime.strftime(max(pd.to_datetime(df["Timestamp"])), '%Y-%m-%dT%H:%M:%S.000Z')


def log_in(driver):

	driver.get('https://www.twitter.com/login')

	sleep(4)

	user = "bokudakgainaimachi@gmail.com"#input('username: ')
	my_password = "mmm010203"#getpass('Password: ')

	username = driver.find_element_by_xpath('//input[@name="session[username_or_email]"]')
	username.send_keys(user)

	password = driver.find_element_by_xpath('//input[@name="session[password]"]')
	password.send_keys(my_password)
	password.send_keys(Keys.RETURN)
	sleep(1.5)


def keep_scroling(driver, data, writer, tweet_ids, scrolling, tweet_parsed, limit, scroll, last_position):

	""" scrolling function """

	while scrolling and tweet_parsed<limit:
		#get the card of tweets
		page_cards = driver.find_elements_by_xpath('//div[@data-testid="tweet"]')
		for card in page_cards:
			tweet = get_data(card)
			if tweet:
				#check if the tweet is unique
				tweet_id = ''.join(tweet[:-1])
				if tweet_id not in tweet_ids:
					tweet_ids.add(tweet_id)
					data.append(tweet)
					last_date=str(tweet[2])
					print("Tweet made at: " + str(last_date)+" is found.")
					writer.writerows([tweet])
					tweet_parsed+=1
					if tweet_parsed>=limit:
						break
		scroll_attempt = 0
		while True and tweet_parsed<limit:
			# check scroll position
			print("scroll", scroll)
			#sleep(1)
			driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
			scroll+=1
			sleep(1)
			curr_position = driver.execute_script("return window.pageYOffset;")
			if last_position == curr_position:
				scroll_attempt += 1

				# end of scroll region
				if scroll_attempt >= 2:
					scrolling = False
					break
				else:
					sleep(1) # attempt another scroll
			else:
				last_position = curr_position
				break
	return driver,data,writer, tweet_ids, scrolling, tweet_parsed, scroll, last_position
