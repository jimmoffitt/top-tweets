#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0
# http://www.apache.org/licenses/LICENSE-2.0
import os
import argparse
import json
import sys
from datetime import datetime
from time import gmtime, strftime
import logging

import psycopg2 #Writing 'top tweet' metadata to a shared Postgres database.

# The TwitterDev search-tweets-python project does the work of managing the Tweet collection.
# Local version has special code for Heroku deployment.

from searchtweets import (ResultStream,
                          load_credentials,
                          merge_dicts,
                          read_config,
                          write_result_stream,
                          gen_params_from_config)

# 'Some should be in a config thingy' items:
ENGAGEMENTS_MINIMUM = 5
MAX_TOP_TWEETS = 10
# FILE_DIR = './output'          Not doing any file handling on Heroku, just DB i/o.
# FILE_NAME = 'top_tweets.json'

# Just writing to a database.
TABLE_NAME = os.getenv('TABLE_NAME', None)
DATABASE_NAME = os.getenv('DATABASE_NAME', None)
DATABASE_HOST = os.getenv('DATABASE_HOST', None)
DATABASE_USER = os.getenv('DATABASE_USER', None)
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', None)

logger = logging.getLogger()
# we want to leave this here and have it command-line configurable via the
# --debug flag
logging.basicConfig(level=os.environ.get("LOGLEVEL", "ERROR"))

# REQUIRED_KEYS = {"query", "endpoint"}  #TODO: seems odd to have these details here in a library client.
# With Heroku updates, no command line arguments are required.
# Query is read in from ENV (and file), and over-written with command-line.
REQUIRED_KEYS = {}

def do_set_up(args_dict):
    if args_dict.get("debug") is True:
        logger.setLevel(logging.DEBUG)
        logger.debug("command line args dict:")
        logger.debug(json.dumps(args_dict, indent=4))

    if args_dict.get("config_filename") is not None:
        configfile_dict = read_config(args_dict["config_filename"])
    else:
        configfile_dict = {}

    # extra_headers_str = args_dict.get("extra_headers")
    # if extra_headers_str is not None:
    #     args_dict['extra_headers_dict'] = json.loads(extra_headers_str)
    #     del args_dict['extra_headers']

    logger.debug("config file ({}) arguments sans sensitive args:".format(args_dict["config_filename"]))
    logger.debug(json.dumps(_filter_sensitive_args(configfile_dict), indent=4))

    creds_dict = load_credentials(filename=args_dict["credential_file"],
                                  yaml_key=args_dict["credential_yaml_key"],
                                  env_overwrite=args_dict["env_overwrite"])
    # Do checks and load in from ENV is missing...


    dict_filter = lambda x: {k: v for k, v in x.items() if v is not None}

    config_dict = merge_dicts(dict_filter(configfile_dict),
                              dict_filter(creds_dict),
                              dict_filter(args_dict))

    logger.debug("combined dict (cli, config, creds):")
    logger.debug(json.dumps(_filter_sensitive_args(config_dict), indent=4))

    if len(dict_filter(config_dict).keys() & REQUIRED_KEYS) < len(REQUIRED_KEYS):
        print(REQUIRED_KEYS - dict_filter(config_dict).keys())
        logger.error("ERROR: not enough arguments for the script to work")
        sys.exit(1)

    stream_params = gen_params_from_config(config_dict)
    logger.debug("full arguments passed to the ResultStream object sans credentials")
    logger.debug(json.dumps(_filter_sensitive_args(stream_params), indent=4))

    return stream_params

def parse_cmd_args():
    argparser = argparse.ArgumentParser()
    help_msg = """configuration file with all parameters. Far,
          easier to use than the command-line args version.,
          If a valid file is found, all args will be populated,
          from there. Remaining command-line args,
          will overrule args found in the config,
          file."""

    argparser.add_argument("--query",
                           dest="query",
                           default=None,
                           help="Search query. ")

    argparser.add_argument("--tweet-fields",
                           dest="tweet_fields",
                           default=None,
                           help="Tweet fields of interest. ")

    argparser.add_argument("--expansions",
                           dest="expansions",
                           default=None,
                           help="Object expansions of interest. ")

    argparser.add_argument("--max-top-tweets",
                           dest="max_top_tweets",
                           default=None,
                           help="How many top Tweets to generate. Top 10? ")

    argparser.add_argument("--credential-file",
                           dest="credential_file",
                           default=None,
                           help=("Location of the yaml file used to hold "
                                 "your credentials."))

    argparser.add_argument("--credential-file-key",
                           dest="credential_yaml_key",
                           default="search_tweets_v2",
                           help=("the key in the credential file used "
                                 "for this session's credentials. "
                                 "Defaults to search_tweets_v2"))

    argparser.add_argument("--env-overwrite",
                           dest="env_overwrite",
                           default=True,
                           help=("""Overwrite YAML-parsed credentials with
                                 any set environment variables. See API docs or
                                 readme for details."""))

    argparser.add_argument("--config-file",
                           dest="config_filename",
                           default=None,
                           help=help_msg)

    argparser.add_argument("--start-time",
                           dest="start_time",
                           default=None,
                           help="""Start of datetime window, format 'YYYY-mm-DDTHH:MM' (default: -7 days for /recent, -30 days for /all)""")

    argparser.add_argument("--end-time",
                           dest="end_time",
                           default=None,
                           help="""End of datetime window, format
                                 'YYYY-mm-DDTHH:MM' (default: to 30 seconds before request time)""")

    argparser.add_argument("--results-per-call",
                           dest="results_per_call",
                           help="Number of results to return per call "
                                "(default 10; max 100) - corresponds to "
                                "'max_results' in the API")

    # client options.
    argparser.add_argument("--max-tweets", dest="max_tweets",
                           type=int,
                           help="Maximum number of Tweets to return for this session of requests.")

    argparser.add_argument("--max-pages",
                           dest="max_pages",
                           type=int,
                           default=None,
                           help="Maximum number of pages/API calls to "
                                "use for this session.")

    argparser.add_argument("--output-format",
                       dest="output_format",
                       default="r",
                       help="""Set output format: 
                                   'r' Unmodified API [R]esponses. (default).
                                   'a' [A]tomic Tweets: Tweet objects with expansions inline.
                                   'm' [M]essage stream: Tweets, expansions, and pagination metadata as a stream of messages.""")

    argparser.add_argument("--results-per-file", dest="results_per_file",
                           default=None,
                           type=int,
                           help="Maximum tweets to save per file.")

    argparser.add_argument("--filename-prefix",
                           dest="filename_prefix",
                           default=None,
                           help="prefix for the filename where tweet "
                                " json data will be stored.")

    argparser.add_argument("--no-print-stream",
                           dest="print_stream",
                           action="store_false",
                           help="disable print streaming")

    argparser.add_argument("--print-stream",
                           dest="print_stream",
                           action="store_true",
                           default=True,
                           help="Print tweet stream to stdout")

    argparser.add_argument("--extra-headers",
                           dest="extra_headers",
                           type=str,
                           default=None,
                           help="JSON-formatted str representing a dict of additional HTTP request headers")

    argparser.add_argument("--debug",
                           dest="debug",
                           action="store_true",
                           default=False,
                           help="print all info and warning messages")
    return argparser

def _filter_sensitive_args(dict_):
    sens_args = ("consumer_key", "consumer_secret", "bearer_token")
    return {k: v for k, v in dict_.items() if k not in sens_args}

def add_up_engagements(tweets):
    engaged_tweets = []

    for tweet in tweets:

        total_engagements = 0

        # Look up public metrics and add them together.
        num_likes = tweet['public_metrics']['like_count']
        total_engagements = total_engagements + num_likes
        num_retweets = tweet['public_metrics']['retweet_count']
        total_engagements = total_engagements + num_retweets
        num_replies = tweet['public_metrics']['reply_count']
        total_engagements = total_engagements + num_replies
        num_quotes = tweet['public_metrics']['quote_count']
        total_engagements = total_engagements + num_quotes

        if total_engagements >= ENGAGEMENTS_MINIMUM:
            # print(f"Tweet with {total_engagements} engagements.")
            details = {}
            details['id'] = tweet['id']
            details['score'] = total_engagements
            details['likes'] = num_likes
            details['retweets'] = num_retweets
            details['replies'] = num_replies
            details['quotes'] = num_quotes

            # Add Tweet and score to list.
            engaged_tweets.append(details)

    return engaged_tweets

def sort_tweets(tweets):
    # How many engaged Tweets?
    print(f"{len(tweets)} Tweets with at least {ENGAGEMENTS_MINIMUM} engagements.")

    tweets = sorted(tweets, key=lambda i: i['score'], reverse=True)

    return tweets

def write_output(tweets, filepath):
    # Let's write JSON, so make a conversion.
    contents = json.dumps(tweets)

    # Write the contents to a file.
    try:
        output_file = open(filepath, 'w')
        output_file.write(contents)
        output_file.close()
    except Exception as e:
        message = f"Error writing contents to {filepath}: {e!r}. "
        logging.error(message)
        print(message)

def write_to_database(top_tweets):

    """
    Receive a (short?) list of 'top Tweets', ranked by public metrics accumulative 'score.'
    Writes this list to the snowbot:top_tweets table.
    Table is wiped clean each time...?


    INSERT INTO top_tweets

    VALUES
    {tweet['tweet_id']}
    {tweet['score']}
    {tweet['likes']}
    {tweet['retweets']}
    {tweet['replies']}
    {tweet['quotes']}
    time.now()
    """

    success = False

    # TODO: Delete the top_tweets table, about to refresh.

    try:

        #Create database connection.
        con = psycopg2.connect(database=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port="5432")
        cur = con.cursor()

        # Delete current top tweets:
        sql = 'DELETE FROM top_tweets;'
        cur.execute(sql)
        con.commit()
        # print("Deleted contents of top_tweet table...")

        for tweet in top_tweets:
            sql = f"INSERT INTO top_tweets (tweet_id,score,likes,retweets,replies,quotes,updated_at) VALUES ({tweet['id']},{tweet['score']},{tweet['likes']},{tweet['retweets']},{tweet['replies']},{tweet['quotes']},'{strftime('%Y-%m-%d %H:%M:%S', gmtime())}');"
            # print(sql)
            cur.execute(sql)
            con.commit()
            success = True

        print('Wrote top Tweets to database top_tweets table... ')

    except Exception as e:
        message = f"Error with INSERT: {e}"
        print(message)
        success = False

    con.close()

    return success

def main():
    # The usage pattern here is to make one daily request, aligned to midnight PST, requesting at 3 AM.
    # So, set up the start and end times.
    # print(f"Basing start and end times on current time: {datetime.now()}")
    # ts = datetime.now()
    # start_time = f"{ts.year}-{ts.month}-{ts.day - 3}T{ts.hour - 3}:00:00Z"
    # end_time = f"{ts.year}-{ts.month}-{ts.day-2}T{ts.hour - 3}:00:00Z"
    # print(f"Collecting matched Tweets from {start_time} to {end_time}")

    # Doing some house-keeping, setting up logging, reading in config file, and loading creds.
    args_dict = vars(parse_cmd_args().parse_args())
    max_top_tweets = MAX_TOP_TWEETS
    if args_dict['max_top_tweets'] is not None:
        max_top_tweets = args_dict['max_top_tweets']

    stream_params = do_set_up(args_dict)

    # Create an object that will return Tweets.
    rs = ResultStream(tweetify=False, **stream_params)
    logger.debug(str(rs))

    stream = rs.stream()

    engaged_tweets = []  # {id,engagements}
    total_tweets = 0

    # Parse response, and iterate through Tweet array.
    for response in stream:
        tweets = response['data']
        total_tweets = total_tweets + len(tweets)
        print(f"{len(tweets)} Tweets in response. ")

        engaged_tweets = add_up_engagements(tweets)

    print(f"Collected {total_tweets} Tweets.")
    sorted_tweets = sort_tweets(engaged_tweets)

    top_tweets = sorted_tweets[:int(max_top_tweets)]

    logger.debug(f"Top {max_top_tweets} Tweets:")
    for tweet in top_tweets:
        logger.debug(f"{tweet['score']} engagements: https://twitter.com/author/status/{tweet['id']}")

    write_to_database(top_tweets)
    # write_output(sorted_tweets, f"{FILE_DIR}/{FILE_NAME}")

if __name__ == '__main__':
    main()
