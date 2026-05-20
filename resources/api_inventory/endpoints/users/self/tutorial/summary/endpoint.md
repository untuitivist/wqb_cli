# `/users/self/tutorial/summary`

- URL template: `https://api.worldquantbrain.com/users/self/tutorial/summary`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Tutorial summary state. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/users/self/tutorial/summary`
- Allowed methods: `GET, POST, PATCH, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "active": "bool",
  "expired": "bool",
  "startDatetime": "NoneType",
  "completionDate": "NoneType",
  "expireDatetime": "NoneType",
  "currentStep": "NoneType",
  "maxUnlockedStep": "NoneType",
  "totalSteps": "int",
  "status": "NoneType",
  "notificationSlug": "NoneType"
}
```

## Endpoint Tests

### `GET /users/self/tutorial/summary`

- Status: `tested`
- Tested path: `/users/self/tutorial/summary`
- HTTP: `200 OK`
- Elapsed: `271 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, PATCH, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "active": "bool",
  "completionDate": "null",
  "currentStep": "null",
  "expireDatetime": "null",
  "expired": "bool",
  "maxUnlockedStep": "null",
  "notificationSlug": "null",
  "startDatetime": "null",
  "status": "null",
  "totalSteps": "int"
}
```
