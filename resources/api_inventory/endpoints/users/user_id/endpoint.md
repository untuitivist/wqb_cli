# `/users/{user_id}`

- URL template: `https://api.worldquantbrain.com/users/{user_id}`
- Methods: `GET`
- Sources: `platform_dynamic_capture, rocky-d/wqb`
- Safe probe: `False`
- Description: User profile by id.

## Probe

- Skipped

## Dynamic Capture

### `GET /users/JL40454`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "address": {
    "city": "str",
    "country": "str",
    "postalCode": "null",
    "state": "null",
    "street": "null"
  },
  "approved": "bool",
  "auxiliary": {
    "campaign": {
      "campaign": "str",
      "content": "str",
      "medium": "str",
      "source": "str",
      "term": "null"
    }
  },
  "dateApproved": "str",
  "dateCreated": "str",
  "dateVerified": "str",
  "education": {
    "degree": "str",
    "gpa": "float",
    "graduationYear": "int",
    "major": "str",
    "maxGPA": "float",
    "stem": "bool",
    "university": "str"
  },
  "email": "str",
  "employment": "null",
  "firstName": "str",
  "fullName": "str",
  "gender": "str",
  "geniusLevel": "str",
  "id": "str",
  "image": {
    "url": "str"
  },
  "lastName": "str",
  "onboarding": {
    "status": "str"
  },
  "recruitment": {
    "codingProficiency": "str",
    "englishProficiency": "str",
    "roleInterest": [
      "str"
    ]
  },
  "resume": {
    "dateCreated": "str"
  },
  "settings": {
    "allowTracking": "bool",
    "client": {},
    "communication": {
      "allowSMS": "bool"
    },
    "privacy": {
      "image": {
        "moderation": "str",
        "visibility": "str"
      },
      "name": {
        "moderation": "str",
        "visibility": "str"
      }
    }
  },
  "telephone": "str",
  "verified": "bool"
}
```

## Endpoint Tests

### `GET /users/{user_id}`

- Status: `tested`
- Tested path: `/users/JL40454`
- HTTP: `200 OK`
- Elapsed: `307 ms`
- Content-Type: `application/json`
- Allow: `GET, PUT, PATCH, DELETE, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "address": {
    "city": "str",
    "country": "str",
    "postalCode": "null",
    "state": "null",
    "street": "null"
  },
  "approved": "bool",
  "auxiliary": {
    "campaign": {
      "campaign": "str",
      "content": "str",
      "medium": "str",
      "source": "str",
      "term": "null"
    }
  },
  "dateApproved": "str",
  "dateCreated": "str",
  "dateVerified": "str",
  "education": {
    "degree": "str",
    "gpa": "float",
    "graduationYear": "int",
    "major": "str",
    "maxGPA": "float",
    "stem": "bool",
    "university": "str"
  },
  "email": "str",
  "employment": "null",
  "firstName": "str",
  "fullName": "str",
  "gender": "str",
  "geniusLevel": "str",
  "id": "str",
  "image": {
    "url": "str"
  },
  "lastName": "str",
  "onboarding": {
    "status": "str"
  },
  "recruitment": {
    "codingProficiency": "str",
    "englishProficiency": "str",
    "roleInterest": [
      "str"
    ]
  },
  "resume": {
    "dateCreated": "str"
  },
  "settings": {
    "allowTracking": "bool",
    "client": {},
    "communication": {
      "allowSMS": "bool"
    },
    "privacy": {
      "image": {
        "moderation": "str",
        "visibility": "str"
      },
      "name": {
        "moderation": "str",
        "visibility": "str"
      }
    }
  },
  "telephone": "str",
  "verified": "bool"
}
```
