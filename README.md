# Pixeldrain-Refresher
Automatically renew file expiration on Pixeldrain

### Settings
##### Rename `.env.example` to `.env` and change the following values
- API_KEY : Get your Pixeldrain API Key [Here](https://pixeldrain.com/user/api_keys "Here")

### Run
##### Docker
------------
Using `docker compose up -d` to build image and create container

The compose plugins will automatically load environment from .env
##### CLI
------------
1. Create virtual environment `python3 -m venv {yourvenvname}`
2. Activate virtual environment `source {yourvenvname}/bin/activate`
3. Install dependencies `python3 -m pip install --no-cache-dir -r requirements.txt`
4. Run the app `python3 main.py`