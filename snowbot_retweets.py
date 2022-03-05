# This script collects Tweets that match a query, then surfaces a 'most relevant' Tweet to quote.
# It makes requests to v2 Recent search and Post Tweets endpoints:
#   * GET /2/tweets/search/recent query, start_time
#   * POST /2/tweets text, quote_tweet_id
#
# This script uses 'relevancy' sorting to efficiently surface higher-engaged Tweets.
# The script requests 100 Tweets per response, and, given the sort order, it assumes
# the most relevant Tweets is included with the first response. For that reason, this
# script does not paginate through search responses.
#
# Since the underlying search 'revelant ranking' model is evolving and will always have an
# element of 'secret sauce' to rank relevance, there is an additional layer of ranking
# performed by this script. This script ranks the *first page* of search results (the only
# one requested) by their number of Likes and Retweets (these public metrics are available
# Tweet attributes.
#
# Note: This script was written to run on Heroku. Instead of passing in settings and options
# via the command-line, these inputs are read from the local environment and no command-line
# options are supported.

import requests
from requests_oauthlib import OAuth1Session
import os
import json
import datetime
from dateutil.relativedelta import *

# Retrieve authentication tokens.
# Here, the Author consumer and user tokens needed to Retweet on behalf of the Author's account.
bot_consumer_key = os.environ.get("SNOWBOT_CONSUMER_KEY")
bot_consumer_secret = os.environ.get("SNOWBOT_CONSUMER_SECRET")
author_access_token = os.environ.get("SNOWBOT_ACCESS_TOKEN")
author_access_secret = os.environ.get("SNOWBOT_ACCESS_SECRET")
# Using search endpoint with App-level Bearer Token.
search_bearer_token = os.environ.get("SEARCHTWEETS_BEARER_TOKEN")

def set_quote_text(query):

    # TODO: Change this up and make more dynamic...

    text = f"Surfacing this Tweet with the v2 Recent search endpoint, sorting by relevancy. \n\nSearching for Tweets from the " \
           f"last 24 hours that match this filter: #{query}"

    #text = "This is some new test text to quote with... "

    return text

def quote_tweet(tweet_id, query):

    quote_text = set_quote_text(query)
    payload = {"text": quote_text, "quote_tweet_id": tweet_id}

    # Make the request
    oauth = OAuth1Session(
        bot_consumer_key,
        client_secret=bot_consumer_secret,
        resource_owner_key=author_access_token,
        resource_owner_secret=author_access_secret
    )

    # Making the request...
    response = oauth.post(
        "https://api.twitter.com/2/tweets", json=payload
    )

    if response.status_code != 200:
        print(f"Response code: {response.status_code}")
    #    raise Exception(
    #        "Request returned an error: {} {}".format(response.status_code, response.text)
    #    )

    return response

def retweet(author_id, tweet_id):

    # You can replace the given Tweet ID with your the Tweet ID you want to Retweet
    # You can find a Tweet ID by using the Tweet lookup endpoint
    payload = {"tweet_id": tweet_id}

    # Make the request
    oauth = OAuth1Session(
        bot_consumer_key,
        client_secret=bot_consumer_secret,
        resource_owner_key=author_access_token,
        resource_owner_secret=author_access_secret
    )

    # Making the request...
    response = oauth.post(
        "https://api.twitter.com/2/users/{}/retweets".format(author_id), json=payload
    )

    if response.status_code != 200:
        print(f"Response code: {response.status_code}")
    #    raise Exception(
    #        "Request returned an error: {} {}".format(response.status_code, response.text)
    #    )

    return response

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    r.headers["Authorization"] = f"Bearer {search_bearer_token}"
    r.headers["User-Agent"] = "@SnowbotDev snowbot_retweets.py"
    return r

def get_start_time(start_time_hours_ago):
    timestamp = datetime.datetime.utcnow()
    timestamp = (timestamp + relativedelta(hours=-int(start_time_hours_ago)))
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

def search_tweets(query, start_time_hours_ago):
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    start_time = get_start_time(start_time_hours_ago)
    query_params = {'query': query, 'sort_order': 'relevancy','start_time': start_time, 'tweet.fields': 'public_metrics', 'max_results': 100}
    response = requests.get(search_url, auth=bearer_oauth, params=query_params)

    if response.status_code != 200:
        print(f"Response code: {response.status_code}")
    #    raise Exception(
    #        "Request returned an error: {} {}".format(response.status_code, response.text)
    #    )

    return response

if __name__ == '__main__':

    author_id = os.environ.get("AUTHOR_ID")
    # Retreive some 'app' settings (things that would
    query = os.environ.get("query")
    metrics_minimum = os.environ.get("metrics_minimum")
    start_time_hours_ago = os.environ.get("start_time_hours_ago")

    print(f"Making search request with query: #{query}...")
    response = search_tweets(query, start_time_hours_ago)

    # Cast response JSON into a dictionary.
    response_dict = json.loads(response.text)

    if 'data' in response_dict.keys():
        tweets = response_dict['data']

        treshold_met = False

        # For now, just sort by number of Likes + Retweets.
        tweets = sorted(tweets, key=lambda i: i['public_metrics']['like_count']+i['public_metrics']['retweet_count'] , reverse=True)

        if (tweets[0]['public_metrics']['like_count']+ tweets[0]['public_metrics']['retweet_count']) > int(metrics_minimum):
            treshold_met = True

        if treshold_met:
            print(f"https://twitter.com/SnowBotDev/status/{id})")
            tweet_id = tweets[0]['id']
            #response = retweet(author_id, tweet_id)
            response = quote_tweet(tweet_id, query)
    else:
        print("No Tweets from search requests.")
