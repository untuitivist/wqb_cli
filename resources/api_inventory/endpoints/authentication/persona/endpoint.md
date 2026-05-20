# `/authentication/persona`

- URL template: `https://api.worldquantbrain.com/authentication/persona`
- Methods: `GET`
- Sources: `platform_frontend`
- Safe probe: `True`
- Description: Discovered from platform frontend bundle.

## Probe

- Probe URL: `https://api.worldquantbrain.com/authentication/persona`
- Allowed methods: `GET, POST, HEAD, OPTIONS`
- Status: `400 Bad Request`
- Usable GET: `False`

### Response Shape

```json
[
  "str"
]
```

## Official Notes

```json
{
  "summary": "Persona 生物识别/浏览器认证入口。",
  "notes": [
    "POST /authentication 如果返回 401 且 WWW-Authenticate 为 persona，应打开 Location 指向的 URL 完成浏览器认证。",
    "完成后再次请求 Location URL 以完成会话认证。"
  ]
}
```

## Endpoint Tests

### `GET /authentication/persona`

- Status: `tested`
- Tested path: `/authentication/persona`
- HTTP: `400 Bad Request`
- Elapsed: `266 ms`
- Content-Type: `application/json`
- Allow: `GET, POST, HEAD, OPTIONS`

#### Tested Response Shape

```json
[
  "str"
]
```
