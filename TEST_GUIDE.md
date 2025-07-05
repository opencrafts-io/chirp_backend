# Chirp Testing Strategy Guide

## Overview

This document outlines the comprehensive Test-Driven Development (TDD) strategy implemented for the Chirp social media platform. The testing strategy covers all aspects of the application including models, serializers, views, endpoints, middleware, and integration workflows.

## Test Structure

```
Project Testing Structure:
├── tweets/tests/
│   ├── __init__.py
│   ├── test_models.py       # Tweet model validation & constraints
│   ├── test_serializers.py  # StatusSerializer validation & field handling
│   ├── test_views.py        # TweetsListCreateView GET/POST logic
│   └── test_endpoints.py    # HTTP endpoints with JWT authentication
├── groups/tests/
│   ├── __init__.py
│   ├── test_models.py       # Group, GroupPost, GroupInvite models
│   ├── test_serializers.py  # All group serializers validation
│   ├── test_views.py        # Complex group permissions & business logic
│   └── test_endpoints.py    # Group endpoints with authentication
├── dmessages/tests/
│   ├── __init__.py
│   ├── test_models.py       # Message model validation
│   ├── test_serializers.py  # MessageSerializer validation
│   ├── test_views.py        # MessageListCreateView filtering logic
│   └── test_endpoints.py    # Direct messaging endpoints
└── chirp/tests/
    ├── __init__.py
    ├── test_middleware.py   # JWT middleware authentication
    └── test_integration.py  # End-to-end workflows
```

## Running Tests

### Run All Tests
```bash
python manage.py test
```

### Run Tests by App
```bash
# Test tweets app only
python manage.py test tweets

# Test groups app only
python manage.py test groups

# Test dmessages app only
python manage.py test dmessages

# Test middleware and integration
python manage.py test chirp
```

### Run Specific Test Categories
```bash
# Test all models
python manage.py test tweets.tests.test_models groups.tests.test_models dmessages.tests.test_models

# Test all serializers
python manage.py test tweets.tests.test_serializers groups.tests.test_serializers dmessages.tests.test_serializers

# Test all views
python manage.py test tweets.tests.test_views groups.tests.test_views dmessages.tests.test_views

# Test all endpoints
python manage.py test tweets.tests.test_endpoints groups.tests.test_endpoints dmessages.tests.test_endpoints
```

### Run with Verbose Output
```bash
python manage.py test --verbosity=2
```

### Run Specific Test Classes or Methods
```bash
# Run specific test class
python manage.py test tweets.tests.test_models.TweetsModelTest

# Run specific test method
python manage.py test tweets.tests.test_models.TweetsModelTest.test_create_valid_tweet
```

## Test Coverage Areas

### 1. **Model Tests**
- **Purpose**: Validate data integrity, constraints, and business rules
- **Coverage**:
  - Field validation (required fields, max lengths, data types)
  - Model relationships and foreign keys
  - Custom model methods and properties
  - Database constraints and unique fields
  - Edge cases and boundary conditions

### 2. **Serializer Tests**
- **Purpose**: Ensure proper data serialization/deserialization and validation
- **Coverage**:
  - Valid data serialization
  - Invalid data handling and error messages
  - Read-only field protection
  - Field-level validation
  - Custom serializer methods
  - Nested serialization

### 3. **View Tests**
- **Purpose**: Test business logic, permissions, and request handling
- **Coverage**:
  - GET/POST request handling
  - Authentication and authorization
  - Permission boundaries (admin vs member vs non-member)
  - Data filtering and queryset logic
  - Error handling and edge cases
  - Response format validation

### 4. **Endpoint Tests**
- **Purpose**: End-to-end API testing with real HTTP requests
- **Coverage**:
  - JWT authentication flow
  - HTTP status codes and response formats
  - Request/response data validation
  - Authentication edge cases
  - Content-type handling
  - Method validation (GET/POST/PUT/DELETE)

### 5. **Middleware Tests**
- **Purpose**: Test JWT authentication middleware
- **Coverage**:
  - Valid JWT token processing
  - Invalid/expired token handling
  - Authorization header parsing
  - User ID extraction from JWT
  - Error response formatting

### 6. **Integration Tests**
- **Purpose**: Test complete user workflows across multiple apps
- **Coverage**:
  - User registration → tweet creation → group management
  - Group creation → member invitation → messaging
  - Permission enforcement across apps
  - Data consistency across models
  - Cross-app feature interactions

## Key Test Patterns

### 1. **Authentication Mocking**
All tests use mocked JWT authentication to simulate different users:
```python
@patch('tweets.middleware.jwt.decode')
def test_with_auth(self, mock_jwt_decode):
    mock_jwt_decode.return_value = {'sub': 'user123'}
    # Test implementation
```

### 2. **Permission Testing**
Tests verify that users can only access data they have permissions for:
- Group members vs non-members
- Group admins vs regular members
- Message privacy (sender/recipient only)
- Public timeline access

### 3. **Data Validation**
Comprehensive validation testing including:
- Required fields
- Field length limits
- Data type validation
- Custom business rule validation

### 4. **Error Handling**
Tests verify proper error responses:
- 400 Bad Request for invalid data
- 401 Unauthorized for missing/invalid JWT
- 403 Forbidden for permission violations
- 404 Not Found for missing resources

## Test Data Management

### Setup Methods
Each test class has a `setUp()` method that creates test data:
- Sample users with different roles
- Test groups with various membership configurations
- Sample messages and tweets
- Mock JWT tokens for authentication

### Test Isolation
- Each test method runs in isolation with fresh test data
- Database transactions are rolled back after each test
- No test data persists between test runs

## Expected Test Results

### Test Counts by App
- **Tweets**: ~40 tests (models, serializers, views, endpoints)
- **Groups**: ~120 tests (3 models × multiple serializers and complex views)
- **DMessages**: ~35 tests (simpler app with fewer features)
- **Middleware**: ~25 tests (JWT authentication edge cases)
- **Integration**: ~15 tests (cross-app workflows)

**Total**: ~235 comprehensive tests

### Coverage Goals
- **Model Coverage**: 100% (all fields, methods, and constraints)
- **View Coverage**: 100% (all code paths and business logic)
- **Serializer Coverage**: 100% (all validation scenarios)
- **Endpoint Coverage**: 100% (all HTTP methods and auth scenarios)

## Best Practices Demonstrated

1. **Test Naming**: Descriptive test method names explaining what is being tested
2. **Documentation**: Each test method has a docstring explaining its purpose
3. **Assertions**: Multiple assertions per test to verify all aspects
4. **Edge Cases**: Tests for boundary conditions and error scenarios
5. **Mocking**: Proper use of mocks for external dependencies (JWT)
6. **Data Isolation**: Each test creates its own test data
7. **Real Scenarios**: Integration tests mirror real user workflows

## Running Tests in CI/CD

For continuous integration, use:
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests with coverage
python manage.py test --verbosity=2

# Optional: Generate coverage report
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Troubleshooting

### Common Issues

1. **JWT Settings**: Ensure `JWT_PUBLIC_KEY` is configured in settings
2. **Database**: Tests use SQLite in-memory database by default
3. **Middleware**: Ensure `JWTDecodeMiddleware` is in `MIDDLEWARE` setting
4. **Apps**: Ensure all apps are in `INSTALLED_APPS`

### Test Failures

If tests fail:
1. Check the specific error message and test name
2. Verify database migrations are up to date
3. Ensure all required settings are configured
4. Check for import errors or missing dependencies

This comprehensive testing strategy ensures the Chirp application is robust, secure, and maintainable while following TDD best practices.