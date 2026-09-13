# Chirp Social Media Platform

A Django-based microservice for a simple social media platform called Chirp.

## Features
- 📝 Post and view statuses (posts) with 280 character limit
- 👥 Create and manage groups with admin/member roles
- 📧 Send group invitations and manage memberships
- 💬 Post messages in groups with permission controls
- 📊 Attach polls to posts (single/multi-choice, optional end time, anonymous voting)
- 📩 Send direct messages with privacy protection
- 🔐 JWT-based authentication and authorization
- 🏥 Health check endpoint for server monitoring.

## Project Structure
- `chirp/` - Main Django project settings, URLs, and JWT utilities
- `posts/` - Status (post) related logic and API endpoints
- `groups/` - Group management logic with permission system
- `dmessages/` - Direct messaging logic with privacy controls
- `*/tests/` - Comprehensive tests

## Technology Stack
- **Backend**: Django 5.2.3, Django REST Framework
- **Database**: PostgreSQL (recommended) / SQLite (development)
- **Authentication**: JWT tokens with HS256 algorithm
- **Testing**: Django TestCase, APIClient
## Prerequisites
- Python 3.8+
- PostgreSQL 12+ (for production)
- Git

## Setup Instructions

### 1. Clone the Repository
```bash
git clone git@github.com:opencrafts-io/chirp_backend.git
cd chirp
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### For Production (PostgreSQL)
```bash
1. Install PostgreSQL
2. Start PostgreSQL service
3. Create database and user
```

In PostgreSQL shell:
```sql
CREATE DATABASE chirp_db;
CREATE USER chirp_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE chirp_db TO chirp_user;
ALTER USER chirp_user CREATEDB;
\q
```

#### For Development (SQLite)
SQLite is configured by default and requires no additional setup.

### 5. Environment Configuration

Create a `.env` file in the project root

### 6. Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Start the Server
```bash
python manage.py runserver 0.0.0.0:8000
```

### 8. Verify Server is Running
Test the health check endpoint:
```bash
curl http://localhost:8000/ping/
# Expected response: {"message": "Bang."}
```

## API Endpoints

### Authentication
All endpoints except `/ping/` require JWT authentication:
```bash
Authorization: Bearer <jwt_token>
```

### Main Endpoints
- `GET /ping/` - Health check (no auth required)
- `GET|POST /statuses/` - View/create posts
- `GET|POST /groups/` - View/create groups
- `GET /groups/discover/` - Discover all available groups with membership status
- `POST /groups/{group_name}/join/` - Join a group
- `POST /groups/{group_name}/leave/` - Leave a group
- `POST /groups/{group_name}/add_member/` - Add member to group (admin only)
- `POST /groups/{group_name}/invite/` - Invite user to group (admin only)
- `POST /groups/accept_invite/{invite_id}/` - Accept group invitation
- `GET|POST /groups/{group_name}/posts/` - View/create group posts
- `GET|POST /messages/` - View/send direct messages

### Polls
A post may carry a poll. Every post payload includes `poll` (`null` when absent):

```json
{
  "id": 41, "post": 1203, "question": "Which unit first?",
  "allows_multiple": false, "is_anonymous": false, "ends_at": "2026-09-14T18:00:00Z",
  "total_votes": 27, "my_votes": [88],
  "options": [{ "id": 87, "text": "Calculus", "position": 0, "vote_count": 12 }]
}
```

- `POST /posts/create/` — add `"poll": {"question", "allows_multiple", "is_anonymous", "ends_at"?, "options": [{"text", "position"}]}` to the normal body. Rules: question 3–200 chars, 2–10 options of 1–100 chars, case-insensitively unique, `ends_at` ≥ 5 minutes ahead. Polls can't be edited after creation.
- `POST /polls/{poll_id}/vote/` `{"option_ids": [88]}` — **replaces** the caller's selection (single-choice polls accept exactly one id). Returns the updated poll. `400` when the poll is closed or an id doesn't belong to it.
- `DELETE /polls/{poll_id}/vote/` — retracts the caller's selection (idempotent). Returns the updated poll. `400` once the poll has closed, so final results stay final.
- `GET /polls/{poll_id}/voters/?option_id=&page=&page_size=` — paginated voters `{user_id, user, option_ids, voted_at}`. On anonymous polls only the post author may call this (`403` otherwise).

All three poll endpoints apply feed visibility rules: `403` for non-members of a private community, for banned members, and when the caller and the post author have blocked each other.

`total_votes` counts distinct voters; `vote_count` is per option. Both are recomputed inside the vote transaction.

### Example Usage
```bash
# Health check
curl http://localhost:8000/ping/

# Create post (requires JWT)
curl -X POST -H "Authorization: Bearer <jwt_token>" \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello, Chirp!"}' \
     http://localhost:8000/statuses/

# Discover all groups
curl -H "Authorization: Bearer <jwt_token>" \
     http://localhost:8000/groups/discover/

# Join a group
curl -X POST -H "Authorization: Bearer <jwt_token>" \
     http://localhost:8000/groups/my-group/join/

# Leave a group
curl -X POST -H "Authorization: Bearer <jwt_token>" \
     http://localhost:8000/groups/my-group/leave/
```

## Testing

### Comprehensive Test Suite
The project includes tests:
- **Model Tests**
- **Serializer Tests**
- **View Tests**
- **Endpoint Tests**
- **Middleware Tests**
- **Integration Tests**

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test posts.tests
python manage.py test groups.tests
python manage.py test dmessages.tests

# Run with verbose output
python manage.py test --verbosity=2

# Run specific test categories
python manage.py test posts.tests.test_models
python manage.py test groups.tests.test_endpoints
python manage.py test chirp.tests.test_middleware
```

## Development Workflow
### 1. Create Feature Branch
```bash
git checkout -b feature/new-feature
```

### 2. Write Tests First (TDD)
```bash
# Add tests to appropriate test file
python manage.py test path.to.new.tests
```

### 3. Implement Feature
```bash
# Write code to make tests pass
python manage.py test
```

### 4. Run Full Test Suite
```bash
python manage.py test --verbosity=2
```

### 5. Commit Changes
```bash
git add .
git commit -m "Add new feature with tests"
```

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **JWT Errors**: Check JWT_TEST_SECRET in settings
3. **Test Failures**: Run tests individually to isolate issues
4. **Migration Errors**: Reset database with `python manage.py migrate --run-syncdb`


## API Documentation
- OpenAPI spec available in `chirp_openapi.json`
- Import into Postman or Swagger UI for interactive testing

## Production Deployment

## Contributing
1. Fork the repository
2. Create feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## License
This project is licensed under the MIT License.

---

*For more details, see the code in each app's directory and test suites.*
