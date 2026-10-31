# MongoDB setup

You provide the connection string. It is never hardcoded.

## Environment

```
MONGODB_URI=YOUR_MONGODB_CONNECTION_STRING
DATABASE_NAME=fashion_forecasting
```

Local example:

```
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=fashion_forecasting
```

Atlas example (password is yours; do not paste it into git):

```
MONGODB_URI=mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=fashion_forecasting
```

## Atlas checklist (college)

1. Create a free cluster.
2. Database user + password.
3. Network access: allow your IP (or `0.0.0.0/0` only for a short demo).
4. Copy the URI into `.env` (not `.env.example`).

## Test the connection

With MongoDB running (local or Atlas):

```bash
python3 -c "from pymongo import MongoClient; import os
from dotenv import load_dotenv; load_dotenv()
c=MongoClient(os.environ['MONGODB_URI']); print(c.admin.command('ping'))"
```

Or start the API and open `http://localhost:8000/health`.

## Images

Do **not** store raw image binaries in MongoDB. Use Cloudinary URLs if keys are set; otherwise save files under `backend/uploads/` and store the path/URL on the product document.
