# `/users/self`

- URL template: `https://api.worldquantbrain.com/users/self`
- Methods: `GET`
- Sources: `rocky-d/wqb`
- Safe probe: `True`
- Description: Current user profile.

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self`
- Allowed methods: `GET, PUT, PATCH, DELETE, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "id": "str",
  "email": "str",
  "telephone": "str",
  "firstName": "str",
  "lastName": "str",
  "fullName": "str",
  "gender": "str",
  "dateCreated": "str",
  "dateVerified": "str",
  "dateApproved": "str",
  "verified": "bool",
  "approved": "bool",
  "address": {
    "street": "NoneType",
    "city": "str",
    "state": "NoneType",
    "postalCode": "NoneType",
    "country": "str"
  },
  "education": {
    "university": "str",
    "major": "str",
    "degree": "str",
    "stem": "bool",
    "graduationYear": "int",
    "gpa": "float",
    "maxGPA": "float"
  },
  "employment": "NoneType",
  "recruitment": {
    "englishProficiency": "str",
    "codingProficiency": "str",
    "roleInterest": [
      "str"
    ]
  },
  "resume": {
    "dateCreated": "str"
  },
  "image": {
    "url": "str"
  },
  "settings": {
    "allowTracking": "bool",
    "communication": {
      "allowSMS": "bool"
    },
    "privacy": {
      "name": {
        "visibility": "...",
        "moderation": "..."
      },
      "image": {
        "visibility": "...",
        "moderation": "..."
      }
    },
    "client": {}
  },
  "onboarding": {
    "status": "str"
  },
  "auxiliary": {
    "campaign": {
      "campaign": "str",
      "source": "str",
      "medium": "str",
      "term": "NoneType",
      "content": "str"
    }
  },
  "geniusLevel": "str"
}
```

## Endpoint Tests

### `GET /users/self`

- Status: `tested`
- Tested path: `/users/self`
- HTTP: `200 OK`
- Elapsed: `297 ms`
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
