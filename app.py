from email import message
from math import e
import instaloader
import requests
import json
import traceback
from flask import Flask, request, jsonify, render_template_string
import os
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor
import io
import logging
import colorlog

# Set up colorized logger
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'bold_red',
    }
))
logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# If you get an import error, run: pip install colorlog

load_dotenv()

# Cloudflare R2 configuration (fill in your credentials)
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_PUBLIC_URL_BASE = f"https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Remove the upload_to_r2_fileobj function


app = Flask(__name__)

executor = ThreadPoolExecutor(max_workers=4)

def download_instagram_reel(reel_url):
    loader = instaloader.Instaloader()
    try:
        if "instagram.com/reel/" not in reel_url:
            return False, "Invalid Instagram Reel URL."
        shortcode = reel_url.rstrip('/').split('/')[-1]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url
        logger.info(f"Fetched video_url")
        if not video_url:
            return False, "No video URL found for this reel."
        # Save video_url to MongoDB
        send_to_mongodb(video_url)
        return True, f"Reel video URL saved to database."
    except Exception as e:
        logger.error(f"Exception in download_instagram_reel: {e}")
        return False, str(e)

# send r2_url to mongodb
# Get mongodb url from environment variable
MONGODB_URL = os.getenv("MONGODB_URL")
client = MongoClient(MONGODB_URL)
db = client["github-webhook"]
collection = db["reels"]

def send_to_mongodb(video_url):
    try:
        if collection.find_one({"video_url": video_url}):
            logger.info(f"video_url already exists in MongoDB")
            return False
        else:
            logger.info(f"Saving video_url to MongoDB")
        IST = pytz.timezone('Asia/Kolkata')
        created_at = datetime.datetime.now(datetime.timezone.utc).astimezone(IST)
        created_at_time = created_at.strftime("%I:%M %p %d-%m-%Y")
        collection.insert_one({"video_url": video_url, "created_at": created_at_time})
        logger.info(f"Successfully saved video_url to MongoDB")
        return True
    except Exception as e:
        logger.error(f"Failed to save video_url to MongoDB: {str(e)}")
        return False

# List data from MongoDB
@app.route("/reels", methods=["GET"])
def list_reels():
    docs = list(collection.find())
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        # Rename 'video_url' to 'url' for frontend compatibility
        doc["url"] = doc.get("video_url")
        if "video_url" in doc:
            del doc["video_url"]
    return jsonify(docs), 200

@app.route("/", methods=["POST"])
def reels_webhook():
    try:
        if request.is_json:
            payload = request.get_json()
        else:
            payload = json.loads(request.data.decode("utf-8"))
        logger.info(f"{payload}")

        reel_url = payload.get("reel_url")
        if not reel_url:
            return jsonify({"status": "error", "message": "Missing 'reel_url' in paylaod"}), 400
        
        success, message = download_instagram_reel(reel_url)
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 400

    except Exception as e:
        logger.error("Exception in reels_webhook", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("[STARTING] Flask server is starting on port 5000...")
    app.run(port=5000, debug=True)
