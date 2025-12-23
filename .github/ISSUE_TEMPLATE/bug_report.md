---
name: Bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

#  Chirp Service: Bug Report

**Summary:** *A concise title (e.g., [Follows] User follower count not incrementing)*

---

##  Technical Overview
- **Service:** Chirp (Social Features)
- **Endpoint/Method:** `POST /v1/chirp/follow` or `Event: user.created`
- **Impact Area:** (e.g., Newsfeed, User Relationships, Notifications)
- **Environment:** [Local / Staging / Production]

---

##  The Bug
### Description
What is happening at the data or logic level?

### Steps to Reproduce
1. Send request to `...` with Payload:
2. Trigger the event:
3. Check Database/Cache:
4. See Error:

### Expected Behavior
What should the state of the social graph or database be after this action?

---

##  Logs & Data
### API Request/Response
**Request Body:**
```json
{
  "actor_id": "uuid",
  "target_id": "uuid"
}
