# Async Kwork Freelance Exchange Parser

An asynchronous Python parser designed to monitor the Kwork freelance marketplace and instantly stream new orders into a designated Telegram channel. Built with modular architecture, perfect for continuous server deployment.

## 🚀 Features
- **100% Asynchronous:** Built using `aiohttp` and `aiosqlite` for non-blocking I/O operations.
- **Persistent Storage:** Uses an SQLite database to track already processed orders and prevent duplicates.
- **Production Ready:** Environment variables for secure configuration management.
- **Clean Architecture:** Separated modules for database operations, parsing logic, and configuration.

## 🛠️ Tech Stack
- **Language:** Python 3.10+
- **Libraries:** BeautifulSoup4, LXML, Aiohttp, Aiosqlite, Python-dotenv

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/kwork-parser-bot.git](https://github.com/yourusername/kwork-parser-bot.git)
   cd kwork-parser-bot