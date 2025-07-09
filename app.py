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

def upload_to_r2(local_file_path, r2_key):
    session = boto3.session.Session()
    client = session.client(
        's3',
        region_name='auto',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )
    client.upload_file(local_file_path, R2_BUCKET_NAME, r2_key)
    # Generate a presigned URL for GET (valid for 1 hour)
    presigned_url = client.generate_presigned_url(
        'get_object',
        Params={'Bucket': R2_BUCKET_NAME, 'Key': r2_key},
        ExpiresIn=604800  # 1 hour
    )
    return presigned_url

def upload_to_r2_fileobj(fileobj, r2_key):
    session = boto3.session.Session()
    client = session.client(
        's3',
        region_name='auto',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )
    client.upload_fileobj(fileobj, R2_BUCKET_NAME, r2_key)
    presigned_url = client.generate_presigned_url(
        'get_object',
        Params={'Bucket': R2_BUCKET_NAME, 'Key': r2_key},
        ExpiresIn=604800  # 7 days
    )
    return presigned_url


app = Flask(__name__)

executor = ThreadPoolExecutor(max_workers=4)

def upload_and_save_async(dest_path, r2_key):
    try:
        signed_url = upload_to_r2(dest_path, r2_key)
        send_to_mongodb(signed_url)
        os.remove(dest_path)
    except Exception as e:
        logger.error(f"Async upload/save failed: {e}")

def upload_and_save_async_fileobj(file_like, r2_key):
    try:
        file_like.seek(0)
        signed_url = upload_to_r2_fileobj(file_like, r2_key)
        send_to_mongodb(signed_url)
    except Exception as e:
        logger.error(f"Async upload/save failed: {e}")

def download_instagram_reel(reel_url):
    loader = instaloader.Instaloader()
    try:
        if "instagram.com/reel/" not in reel_url:
            return False, "Invalid Instagram Reel URL."
        shortcode = reel_url.rstrip('/').split('/')[-1]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url
        if not video_url:
            return False, "No video URL found for this reel."
        # Stream video into memory
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        file_like = io.BytesIO(response.content)
        r2_key = f"{shortcode}.mp4"
        # Upload to R2 directly from memory
        executor.submit(upload_and_save_async_fileobj, file_like, r2_key)
        # executor.submit(cleanup_old_reels_async)
        return True, f"Reel is being processed and will be available soon."
    except Exception as e:
        logger.error(f"Exception in download_instagram_reel: {e}")
        return False, str(e)

# send r2_url to mongodb
# Get mongodb url from environment variable
MONGODB_URL = os.getenv("MONGODB_URL")
client = MongoClient(MONGODB_URL)
db = client["github-webhook"]
collection = db["reels"]

def send_to_mongodb(r2_url):
    try:
        if collection.find_one({"r2_url": r2_url}):
            logger.info(f"URL already exists in MongoDB: {r2_url}")
            return False
        else:
            logger.info(f"Saving to MongoDB: {r2_url}")
        IST = pytz.timezone('Asia/Kolkata')
        created_at = datetime.datetime.now(datetime.timezone.utc).astimezone(IST)
        created_at_time = created_at.strftime("%I:%M %p %d-%m-%Y")
        collection.insert_one({"r2_url": r2_url, "created_at": created_at_time})
        logger.info(f"Successfully saved to MongoDB: {r2_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to save to MongoDB: {str(e)}")
        return False

# get the list of reels from MongoDB and delete reels that are older than 6 days
# def cleanup_old_reels_async():
#     try:
#         IST = pytz.timezone('Asia/Kolkata')
#         current_time = datetime.datetime.now(datetime.timezone.utc).astimezone(IST)
#         cutoff_time = current_time - datetime.timedelta(days=6)
#         result = collection.delete_many({"created_at": {"$lt": cutoff_time.strftime("%I:%M %p %d-%m-%Y")}})
#         print(f"[INFO] Deleted {result.deleted_count} old reels from MongoDB.")
#     except Exception as e:
#         print(f"[ERROR] Failed to clean up old reels: {str(e)}")

# List data from MongoDB
@app.route("/reels", methods=["GET"])
def list_reels():
    docs = list(collection.find())
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        # Rename 'r2_url' to 'url' for frontend compatibility
        doc["url"] = doc.get("r2_url")
        if "r2_url" in doc:
            del doc["r2_url"]
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
