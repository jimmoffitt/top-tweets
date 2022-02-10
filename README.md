# top-tweets
Python script that uses the Twitter API v2 and TwitterDev's search-tweets-python to surface Tweets with most engagement. 

This script does the following in support of the @SnowbotDev's 'show me top snow Tweets' feature:

* Makes request for all matching Tweets over the past 24 hours for a snow-focused query. 
* The request focuses on public metrics, and includes `tweet.fields=public_metrics`
* The matched Tweets are ranked by their total of public metrics.
* These top Tweets are written to a Postgres database.

This script is hosted on Heroku, and is launched in a worker thread every hour. 

When the @SnowbotDev is asked for top Tweets, it reads from the Postgres database and sends a DM with the top Tweet ID. 
