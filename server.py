from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static')

def get_db_connection():
    return psycopg2.connect(
        dbname="emotionengine",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
        host="localhost"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/emotions/summary')
def get_emotion_summary():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Modified query to exclude 'neutral' emotions
        cur.execute("""
            WITH emotion_counts AS (
                SELECT 
                    c.primary_emotion as emotion,
                    COUNT(*) as count
                FROM comments c
                WHERE c.timestamp > NOW() - INTERVAL '24 hours'
                    AND c.primary_emotion IS NOT NULL
                    AND c.primary_emotion != 'neutral'  -- Exclude neutral emotions
                GROUP BY c.primary_emotion
            )
            SELECT 
                emotion,
                count,
                ROUND((count * 100.0 / (SELECT SUM(count) FROM emotion_counts))::numeric, 1) as percentage
            FROM emotion_counts
            ORDER BY count DESC
        """)
        
        emotions = [{
            "emotion": row[0],
            "count": row[1],
            "percentage": row[2]
        } for row in cur.fetchall()]
        
        # If no data is found, return some dummy data for testing
        if not emotions:
            return jsonify({
                "timeframe": "last 24 hours",
                "emotions": [
                    {"emotion": "No data", "count": 0, "percentage": 0}
                ]
            })
        
        return jsonify({
            "timeframe": "last 24 hours",
            "emotions": emotions
        })
    
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500
    
    finally:
        cur.close()
        conn.close()

@app.route('/emotions/timeline')
def get_emotion_timeline():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get date parameter from request, default to today
    date_param = request.args.get('date')
    
    try:
        # Prepare date filter condition
        if date_param:
            date_filter = f"c.timestamp::date = '{date_param}'::date"
            post_date_filter = f"p.timestamp::date = '{date_param}'::date"
        else:
            date_filter = "c.timestamp > NOW() - INTERVAL '24 hours'"
            post_date_filter = "p.timestamp > NOW() - INTERVAL '24 hours'"
        
        # First query for timeline data
        query = f"""
            WITH hourly_emotions AS (
                SELECT 
                    date_trunc('hour', c.timestamp) as hour,
                    c.primary_emotion,
                    COUNT(*) as count
                FROM comments c
                WHERE {date_filter}
                GROUP BY 
                    date_trunc('hour', c.timestamp),
                    c.primary_emotion
                ORDER BY hour
            )
            SELECT 
                primary_emotion,
                array_agg(to_char(hour, 'YYYY-MM-DD HH24:MI') ORDER BY hour) as times,
                array_agg(count ORDER BY hour) as counts
            FROM hourly_emotions
            GROUP BY primary_emotion
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        # Second query for dominant emotion
        dominant_query = f"""
            SELECT 
                primary_emotion,
                COUNT(*) as count
            FROM comments c
            WHERE {date_filter}
                AND primary_emotion != 'neutral'
            GROUP BY primary_emotion
            ORDER BY count DESC
            LIMIT 1
        """
        
        cur.execute(dominant_query)
        dominant = cur.fetchone()
        dominant_emotion = {
            'emotion': dominant[0] if dominant else 'No data',
            'count': dominant[1] if dominant else 0
        } if dominant else None
        
        # Query for top comment of the day
        top_comment_query = f"""
            SELECT 
                c.comment_text,
                c.author,
                c.score,
                c.primary_emotion
            FROM comments c
            WHERE {date_filter}
            ORDER BY c.score DESC
            LIMIT 1
        """
        
        cur.execute(top_comment_query)
        top_comment_row = cur.fetchone()
        top_comment = {
            'body': top_comment_row[0] if top_comment_row else 'No comments found',
            'author': top_comment_row[1] if top_comment_row else 'N/A',
            'score': top_comment_row[2] if top_comment_row else 0,
            'emotion': top_comment_row[3] if top_comment_row else 'neutral'
        } if top_comment_row else None
        
        # Query for top post of the day
        top_post_query = f"""
            SELECT 
                p.title,
                p.author,
                p.post_id,
                p.post_url
            FROM posts p
            WHERE {post_date_filter}
            ORDER BY p.timestamp DESC
            LIMIT 1
        """
        
        cur.execute(top_post_query)
        top_post_row = cur.fetchone()
        top_post = {
            'title': top_post_row[0] if top_post_row else 'No posts found',
            'author': top_post_row[1] if top_post_row else 'N/A',
            'id': top_post_row[2] if top_post_row else '',
            'url': top_post_row[3] if top_post_row else '#'
        } if top_post_row else None
        
        timestamps = sorted(set(
            time
            for row in results
            for time in row[1]
        ))
        
        emotions = [{
            'name': row[0],
            'values': row[2]
        } for row in results]
        
        return jsonify({
            'timestamps': timestamps,
            'emotions': emotions,
            'dominant_emotion': dominant_emotion,
            'top_comment': top_comment,
            'top_post': top_post
        })
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500
    
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
