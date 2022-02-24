import requests
from requests_oauthlib import OAuth1Session
import os
import json
import datetime
from dateutil.relativedelta import *

#The snowbot uses Twitter App 18554551 for searching and posting Retweets.

#Retrieve authentication tokens.
# Here, the @SnowbotDev consumer and user tokens needed to Retweet on behalf of the @SnowbotDev account.
bot_consumer_key = os.environ.get("SNOWBOT_CONSUMER_KEY")
bot_consumer_secret = os.environ.get("SNOWBOT_CONSUMER_SECRET")
retweeter_access_token = os.environ.get("SNOWBOT_ACCESS_TOKEN")
retweeter_access_secret = os.environ.get("SNOWBOT_ACCESS_SECRET")
# Using search endpoint with App-level Bearer Token.
search_bearer_token = os.environ.get("SEARCHTWEETS_BEARER_TOKEN")

QUERY = os.environ.get("query")
METRICS_MINIMUM = os.environ.get("metrics_minimum")

def get_start_time():
    num_hours = 24
    timestamp = datetime.datetime.utcnow()
    timestamp = (timestamp + relativedelta(hours=-num_hours))
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

def quote_tweet(tweet_id):

    quote_text = f"This Tweet was the most liked Tweet from the last 24 hours that matches this filter: #{QUERY}"

    payload = {"text": quote_text, "quote_tweet_id": tweet_id}

    # Make the request
    oauth = OAuth1Session(
        bot_consumer_key,
        client_secret=bot_consumer_secret,
        resource_owner_key=retweeter_access_token,
        resource_owner_secret=retweeter_access_secret
    )

    # Making the requestresponse = {Response} <Response [403]>
    response = oauth.post(
        "https://api.twitter.com/2/tweets", json=payload
    )

    return response

def retweet(tweet_id):
    # Be sure to replace your-user-id with your own user ID or one of an authenticating user
    # You can find a user ID by using the user lookup endpoint
    id = "906948460078698496" # <-- https://api.twitter.com/2/users/by/username/snowbotdev

    # You can replace the given Tweet ID with your the Tweet ID you want to Retweet
    # You can find a Tweet ID by using the Tweet lookup endpoint
    payload = {"tweet_id": tweet_id}

    # Make the request
    oauth = OAuth1Session(
        bot_consumer_key,
        client_secret=bot_consumer_secret,
        resource_owner_key=retweeter_access_token,
        resource_owner_secret=retweeter_access_secret
    )

    # Making the requestresponse = {Response} <Response [403]>
    response = oauth.post(
        "https://api.twitter.com/2/users/{}/retweets".format(id), json=payload
    )

    return response

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    r.headers["Authorization"] = f"Bearer {search_bearer_token}"
    r.headers["User-Agent"] = "@snowbotdev"
    return r

def build_start_time():
    start_time = ''

    return start_time

def search_tweets():
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    start_time = get_start_time()
    #TODO: add 'start_time': start_time
    query_params = {'query': QUERY, 'sort_order': 'relevancy','start_time': start_time, 'tweet.fields': 'public_metrics', 'max_results': 100}
    response = requests.get(search_url, auth=bearer_oauth, params=query_params)

    print(response)

    return response

if __name__ == '__main__':

    print("Making search request...")
    response = search_tweets()

    # Parse response and grab first Tweet ID
    json_object = json.loads(response.text)

    if 'data' in json_object.keys():
        tweets = json_object['data']

        treshold_met = False

        # For now, just sort by number of Likes.
        tweets = sorted(tweets, key=lambda i: i['public_metrics']['like_count'], reverse=True)

        # for tweet in tweets:
        #     metrics = tweet['public_metrics']
        #     id = tweet['id']
        #     total_metrics = metrics['retweet_count'] + metrics['reply_count'] + metrics['like_count'] + metrics['quote_count']
        #     if total_metrics > int(METRICS_MINIMUM):
        #         treshold_met = True
        #         break

        id = tweets[0]['id']

        #if treshold_met:
        print(f"https://twitter.com/SnowBotDev/status/{id})")
        #response = retweet(id)
        response = quote_tweet(id)
    else:
        print("No Tweets from search requests.")

    #if response.status_code != 200:
    #    raise Exception(
    #        "Request returned an error: {} {}".format(response.status_code, response.text)
    #    )

    #print("Response code: {}".format(response.status_code))

    # Saving the response as JSON
    #json_response = response.json()
    #print(json.dumps(json_response, indent=4, sort_keys=True))

