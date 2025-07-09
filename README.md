# 🎬 ReelsFeed – The Instagram Reel Saver & Streamer 🚀

Welcome to **ReelsFeed**! Your one-stop solution to save and stream your favorite Instagram Reels with love, speed, and style. 💖

---

## ✨ Features
- 🔗 **Save Instagram Reel URLs** to your own database
- ⚡ **Fast, in-memory processing** – no local file clutter
- 🌈 **Beautiful, colorized logs** for easy debugging
- 📱 **Mobile-ready API** for your React Native/Expo frontend
- 🐳 **Dockerized** for easy deployment anywhere
- 💬 **Telegram Bot** integration for sharing reels on the go

---

## 🛠️ Tech Stack
- **Python 3**
- **Flask** (Backend API)
- **MongoDB** (Database)
- **Instaloader** (Instagram scraping)
- **Docker** (Containerization)
- **colorlog** (Pretty logs)
- **React Native/Expo** (Frontend)
- **Telegram Bot** (Optional)

---

## 🚀 Quick Start

### 1. Clone the Repo
```bash
git clone https://github.com/yourusername/reelsfeed.git
cd reelsfeed
```

### 2. Set Up Environment
Create a `.env` file with your secrets:
```
MONGODB_URL=your_mongodb_connection_string
```

### 3. Build & Run with Docker 🐳
```bash
docker build -t reelsfeed:latest .
docker run -p 5004:5004 --env-file .env reelsfeed:latest
```

### 4. API Endpoints
- **POST /** – Save a reel:
  ```json
  { "reel_url": "https://www.instagram.com/reel/xyz..." }
  ```
- **GET /reels** – List all saved reels

---

## 🤖 Telegram Bot (Optional)
- Set your `TOKEN` and `WEBHOOK_URL` in `telegram_bot/.env`
- Run the bot with Docker or locally

---

## 💡 Why You'll Love ReelsFeed
- **No more lost reels!** Save and share with friends anytime
- **Super fast** – no disk I/O, just pure speed
- **Modern, mobile-friendly** – works with your Expo/React Native app
- **Open source & easy to hack** – make it your own!

---

## 🧑‍💻 Contributing
Pull requests, issues, and stars are always welcome! ⭐

---

## 📸 Made with ❤️ by Rohit & Contributors

Enjoy your reels, spread the love, and happy streaming! 🎉 