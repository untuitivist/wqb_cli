# `/authentication`

- URL template: `https://api.worldquantbrain.com/authentication`
- Methods: `DELETE, GET, HEAD, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Authentication session endpoint. / Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/authentication`
- Allowed methods: `GET, POST, DELETE, HEAD, OPTIONS`
- Status: `200 OK`
- Usable GET: `True`

### Response Shape

```json
{
  "user": {
    "id": "str"
  },
  "token": {
    "expiry": "float"
  },
  "permissions": [
    "str"
  ]
}
```

## Official Notes

```json
{
  "summary": "管理当前客户端认证状态。",
  "methods": {
    "GET": {
      "description": "获取当前认证状态。",
      "request": "GET /authentication with Cookie t=<JWT>.",
      "responses": [
        {
          "status": "204 No Content",
          "meaning": "客户端当前未认证。"
        },
        {
          "status": "200 OK",
          "meaning": "客户端已认证，返回 user、token.expiry 和 permissions。"
        }
      ]
    },
    "POST": {
      "description": "使用 Basic Auth 登录。可能要求 reCAPTCHA 或浏览器/persona 认证。",
      "request_body": {
        "recaptcha": "string, optional when required",
        "expiry": "number, seconds, 1..14400"
      },
      "responses": [
        {
          "status": "201 Created",
          "meaning": "登录成功，设置 t cookie。"
        },
        {
          "status": "401 Unauthorized",
          "meaning": "凭证错误或需要额外认证。"
        }
      ]
    },
    "DELETE": {
      "description": "删除认证状态，清空认证 cookie 并使 JWT 失效。",
      "responses": [
        {
          "status": "204 OK",
          "meaning": "登出成功。"
        },
        {
          "status": "401 Unauthorized",
          "meaning": "当前认证状态无效。"
        }
      ]
    }
  }
}
```

## Dynamic Capture

### `GET /authentication`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "permissions": [
    "str"
  ],
  "token": {
    "expiry": "float"
  },
  "user": {
    "id": "str"
  }
}
```

## Endpoint Tests

### `DELETE /authentication`

- Status: `skipped_mutating`
- Tested path: `/authentication`
- Reason: DELETE may mutate remote state; not executed by inventory test.
### `GET /authentication`

- Status: `tested`
- Tested path: `/authentication`
- HTTP: `200 OK`
- Elapsed: `261 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, DELETE, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "permissions": [
    "str"
  ],
  "token": {
    "expiry": "float"
  },
  "user": {
    "id": "str"
  }
}
```
### `HEAD /authentication`

- Status: `tested`
- Tested path: `/authentication`
- HTTP: `200 OK`
- Elapsed: `268 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, DELETE, HEAD, OPTIONS`
### `POST /authentication`

- Status: `skipped_mutating`
- Tested path: `/authentication`
- Reason: POST may mutate remote state; not executed by inventory test.
