# Chirp Social Media Platform

A Django-based microservice for a simple social media platform called Chirp.

## Features
- 📝 Post and view statuses (tweets) with 280 character limit
- 👥 Create and manage groups with admin/member roles
- 📧 Send group invitations and manage memberships
- 💬 Post messages in groups with permission controls
- 📩 Send direct messages with privacy protection
- 🔐 JWT-based authentication and authorization
- 🏥 Health check endpoint for server monitoring

## Project Structure
- `chirp/` - Main Django project settings, URLs, and JWT utilities
- `tweets/` - Status (tweet) related logic and API endpoints
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
- `GET|POST /statuses/` - View/create tweets
- `GET|POST /groups/` - View/create groups
- `POST /groups/{id}/add_member/` - Add member to group
- `POST /groups/{id}/invite/` - Invite user to group
- `POST /groups/accept_invite/{id}/` - Accept group invitation
- `GET|POST /groups/{id}/posts/` - View/create group posts
- `GET|POST /messages/` - View/send direct messages

### Example Usage
```bash
# Health check
curl http://localhost:8000/ping/

# Create tweet (requires JWT)
curl -X POST -H "Authorization: Bearer <jwt_token>" \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello, Chirp!"}' \
     http://localhost:8000/statuses/
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
python manage.py test tweets.tests
python manage.py test groups.tests
python manage.py test dmessages.tests

# Run with verbose output
python manage.py test --verbosity=2

# Run specific test categories
python manage.py test tweets.tests.test_models
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
