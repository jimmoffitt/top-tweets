Database schema: 

CREATE TABLE top_tweets ( 
  tweet_id varchar PRIMARY KEY, 
  score integer DEFAULT 0, 
  likes integer DEFAULT 0, 
  retweets integer DEFAULT 0, 
  quotes integer DEFAULT 0, 
  replies integer DEFAULT 0,
  updated_at timestamp);
  
  
  
Example insert:
  
  INSERT INTO top_tweets (tweet_id,score,likes,retweets,replies,quotes,updated_at) VALUES (1484265578202382336,129,121,4,3,1,2022-01-20 17:40:30.764571);

  
