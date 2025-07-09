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


app = Flask(__name__)

def download_instagram_reel(reel_url):
    loader = instaloader.Instaloader()
    try:
        if "instagram.com/reel/" not in reel_url:
            return False, "Invalid Instagram Reel URL."
        shortcode = reel_url.rstrip('/').split('/')[-1]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        temp_folder = f"temp_reel_{shortcode}"
        loader.download_post(post, target=temp_folder)
        # Find the .mp4 file in the temp folder
        mp4_file = None
        for file in os.listdir(temp_folder):
            if file.endswith(".mp4"):
                mp4_file = file
                break
        if not mp4_file:
            # Clean up temp folder
            for f in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder, f))
            os.rmdir(temp_folder)
            return False, "No .mp4 file found in downloaded content."
        # Create reels folder if it doesn't exist
        os.makedirs("reels", exist_ok=True)
        dest_path = os.path.join("reels", f"{shortcode}.mp4")
        os.rename(os.path.join(temp_folder, mp4_file), dest_path)
        # Clean up temp folder
        for f in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, f))
        os.rmdir(temp_folder)
        # Upload to R2
        r2_key = f"{shortcode}.mp4"
        signed_url = upload_to_r2(dest_path, r2_key)
        # Send signed_url to MongoDB
        send_to_mongodb(signed_url)
        # Remove the local file after upload
        os.remove(dest_path)
        return True, f"Saved reel and uploaded to {signed_url}"
    except Exception as e:
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
            print(f"[INFO] URL already exists in MongoDB: {r2_url}")
            return False
        else:
            print(f"[INFO] Saving to MongoDB: {r2_url}")
        # Create a timestamp for when the reel was created in IST
        IST = pytz.timezone('Asia/Kolkata')
        created_at = datetime.datetime.now(datetime.timezone.utc).astimezone(IST)
        created_at_time = created_at.strftime("%I:%M %p %d-%m-%Y")
        collection.insert_one({"r2_url": r2_url, "created_at": created_at_time})
        print(f"[INFO] Successfully saved to MongoDB: {r2_url}")
        # Clean up old reels
        cleanup_old_reels()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save to MongoDB: {str(e)}")
        return False

# get the list of reels from MongoDB and delete reels that are older than 6 days
def cleanup_old_reels():
    try:
        # Get the current time in UTC
        IST = pytz.timezone('Asia/Kolkata')
        current_time = datetime.datetime.now(datetime.timezone.utc).astimezone(IST)
        # Calculate the cutoff time (6 days ago)
        cutoff_time = current_time - datetime.timedelta(days=6)
        
        # Find and delete old reels
        result = collection.delete_many({"created_at": {"$lt": cutoff_time.strftime("%I:%M %p %d-%m-%Y")}})
        print(f"[INFO] Deleted {result.deleted_count} old reels from MongoDB.")
    except Exception as e:
        print(f"[ERROR] Failed to clean up old reels: {str(e)}")

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
        print(f"[INFO] {payload}")

        reel_url = payload.get("reel_url")
        if not reel_url:
            return jsonify({"status": "error", "message": "Missing 'reel_url' in paylaod"}), 400
        
        success, message = download_instagram_reel(reel_url)
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 400

    except Exception as e:
        print("[ERROR]")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("[STARTING] Flask server is starting on port 5000...")
    app.run(port=5000, debug=True)
