import praw
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from operator import attrgetter
import requests
import time

load_dotenv()

#get sentiment from huggingface
def get_sentiment(text, max_retries=5):
    API_URL = "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json={"inputs": text})
            
            if response.status_code == 200:
                # Get the list of emotions from the response
                emotions = response.json()[0]
                
                # Filter for emotions with score > 0.1 (10%)
                significant_emotions = [
                    emotion for emotion in emotions 
                    if emotion['score'] > 0.1
                ]
                
                # Sort by score and get top 3
                significant_emotions = sorted(
                    significant_emotions, 
                    key=lambda x: x['score'], 
                    reverse=True
                )[:3]
                
                return {
                    'primary_emotion': significant_emotions[0]['label'] if significant_emotions else 'neutral',
                    'emotions': significant_emotions
                }
            elif response.status_code == 503:
                print(f"Model is loading (attempt {attempt + 1}/{max_retries})...")
                time.sleep(20)  # Wait 20 seconds before retrying
                continue
            else:
                print(f"API error: Status code {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return None
    
    print("Max retries reached, model failed to load")
    return None

def main():
    subreddits = ["2007scape"]
    
    for subreddit_name in subreddits:  # Loop through subreddits list
        print(f"\nProcessing r/{subreddit_name}")
        
        # Initialize Reddit instance
        reddit = praw.Reddit(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            user_agent="Data Collector v1.0 by teaxthree"
        )

        # Connect to PostgreSQL database
        conn = psycopg2.connect(
            dbname="emotionengine",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),
            host="localhost"
        )
        cur = conn.cursor()

        try:
            # Access the subreddit
            storecount = 0
            subreddit = reddit.subreddit(subreddit_name)
            
            # Get top 10 non-stickied posts
            top_posts = []
            for post in subreddit.top(time_filter="day", limit=20):  # Get 20 to account for stickied posts
                if not post.stickied:
                    top_posts.append(post)
                    if len(top_posts) == 10:  # Stop after getting 10 non-stickied posts
                        break
            
            print(f"Found {len(top_posts)} top posts from r/{subreddit_name}")
            
            # Process each post
            for post_index, post in enumerate(top_posts, 1):
                print(f"\nProcessing post {post_index}/10: {post.title}")
                
                # Create the post entry
                post_time = datetime.fromtimestamp(post.created_utc)
                cur.execute("""
                    INSERT INTO posts (subreddit, post_id, author, title, post_text, post_url, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    subreddit_name,
                    post.id,
                    str(post.author) if post.author else '[deleted]',  # Handle deleted authors
                    post.title,
                    post.selftext if post.selftext else None,
                    post.url,
                    post_time
                ))
                post_db_id = cur.fetchone()[0]
                
                # If post has text content, store it as a comment
                if post.selftext:
                    sentiment_result = get_sentiment(post.selftext)
                    if sentiment_result:
                        cur.execute("""
                            INSERT INTO comments (
                                post_id, subreddit, comment_id, author, comment_text, 
                                is_post_body, score, primary_emotion, timestamp
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            post_db_id,
                            subreddit_name,
                            f"{post.id}_body",
                            str(post.author) if post.author else '[deleted]',
                            post.selftext,
                            True,
                            post.score,
                            sentiment_result['primary_emotion'],
                            post_time
                        ))
                        comment_id = cur.fetchone()[0]
                        
                        for emotion in sentiment_result['emotions']:
                            cur.execute("""
                                INSERT INTO comment_emotions (comment_id, emotion, score)
                                VALUES (%s, %s, %s)
                            """, (comment_id, emotion['label'], emotion['score']))
                        
                        print(f"Stored post body with primary emotion: {sentiment_result['primary_emotion']}")
                        storecount += 1
                
                # Get comments and sort them
                post.comments.replace_more(limit=0)
                all_comments = list(post.comments.list())
                
                # If we stored the post body, get top 9 comments, otherwise get top 10
                comments_to_get = 9 if post.selftext else 10
                top_comments = sorted(all_comments, key=attrgetter('score'), reverse=True)[:comments_to_get]
                
                print(f"Processing {len(top_comments)} comments for post: {post.title}")
                
                # Store comments in database
                for comment in top_comments:
                    comment_time = datetime.fromtimestamp(comment.created_utc)
                    
                    # Get sentiment for the comment
                    sentiment_result = get_sentiment(comment.body)
                    
                    if sentiment_result:
                        # Insert the comment and get its ID
                        cur.execute("""
                            INSERT INTO comments (
                                post_id, subreddit, comment_id, author, comment_text, 
                                is_post_body, score, primary_emotion, timestamp
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            post_db_id,
                            subreddit_name,
                            comment.id,
                            str(comment.author) if comment.author else '[deleted]',
                            comment.body,
                            False,
                            comment.score,
                            sentiment_result['primary_emotion'],
                            comment_time
                        ))

                        comment_id = cur.fetchone()[0]
                        
                        # Insert each emotion separately
                        for emotion in sentiment_result['emotions']:
                            cur.execute("""
                                INSERT INTO comment_emotions (comment_id, emotion, score)
                                VALUES (%s, %s, %s)
                            """, (comment_id, emotion['label'], emotion['score']))
                        storecount += 1

                # Commit after each post's comments are processed
                conn.commit()

            print("\nAll posts processed successfully!")
            print(f"Total comments stored: {storecount}")

        except Exception as e:
            print(f"An error occurred: {e}")
            conn.rollback()
        
        finally:
            # Close database connection
            cur.close()
            conn.close()

if __name__ == "__main__":
    main()
