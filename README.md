# Chirp Microservice API

This is a Django-based microservice for a simple social platform called Chirp.

## Features
- Post and view statuses (tweets)
- Create and manage groups
- Add or invite members to groups
- Post messages in groups
- Send direct messages

## Project Structure
- `chirp/` - Main Django project settings and URLs
- `tweets/` - Status (tweet) related logic
- `groups/` - Group management logic
- `messages/` - Direct messaging logic

## API Documentation
- An OpenAPI spec is available in `chirp_openapi.json` for use with Postman or Swagger UI.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run migrations:
   ```bash
   python manage.py migrate
   ```
3. Start the server:
   ```bash
   python manage.py runserver
   ```

## Testing
- Import `chirp_openapi.json` into Postman to test endpoints.

---

*For more details, see the code in each app's directory.*
