# `/simulations`

- URL template: `https://api.worldquantbrain.com/simulations`
- Methods: `GET, OPTIONS, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Safe probe: `True`
- Description: Simulation collection and simulation creation. / Discovered from platform frontend bundle.
- Request body: POST creates simulation. Do not auto-probe POST.

## Probe

- Probe URL: `https://api.worldquantbrain.com/simulations`
- Allowed methods: `POST, OPTIONS`
- Status: `405 Method Not Allowed`
- Usable GET: `False`

### Response Shape

```json
{
  "detail": "str"
}
```

## Official Notes

```json
{
  "summary": "创建 simulation 或获取 simulation endpoint 的 OPTIONS schema。",
  "methods": {
    "OPTIONS": {
      "description": "返回 POST 可用字段、类型、必填项和允许值。"
    },
    "POST": {
      "description": "创建一个 REGULAR 或 SUPER simulation。",
      "request_body": {
        "type": "REGULAR or SUPER",
        "settings": {
          "instrumentType": "EQUITY etc.",
          "region": "region",
          "universe": "universe",
          "delay": "0 or 1",
          "decay": "number",
          "neutralization": "neutralization",
          "truncation": "number",
          "pasteurization": "pasteurization",
          "testPeriod": "ISO-8601 duration, e.g. P1Y6M",
          "unitHandling": "unit handling",
          "nanHandling": "nan handling",
          "selectionHandling": "SUPER only",
          "selectionLimit": "SUPER only",
          "language": "FASTEXPR or PYTHON",
          "visualization": "boolean"
        },
        "regular": "REGULAR expression code",
        "combo": "SUPER combo code",
        "selection": "SUPER selection code"
      },
      "multi_simulation": "POST body can be an array of 2..10 compatible simulation objects when permission allows.",
      "responses": [
        {
          "status": "201 Created",
          "meaning": "Location header points to /simulations/<simulation_id>."
        },
        {
          "status": "400 Bad Request",
          "meaning": "Validation errors by field."
        }
      ]
    }
  }
}
```

## Dynamic Capture

### `OPTIONS /simulations`

- Seen count: `22`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "actions": {
    "POST": {
      "alpha": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "children": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "is": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "links": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "location": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "message": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "origin": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "parent": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "progress": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "settings": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "visualizations": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```

## Endpoint Tests

### `GET /simulations`

- Status: `tested`
- Tested path: `/simulations`
- HTTP: `405 Method Not Allowed`
- Elapsed: `257 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "detail": "str"
}
```
### `OPTIONS /simulations`

- Status: `tested`
- Tested path: `/simulations`
- HTTP: `200 OK`
- Elapsed: `270 ms`
- Content-Type: `application/json`
- Allow: `POST, OPTIONS`

#### Tested Response Shape

```json
{
  "actions": {
    "POST": {
      "alpha": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "children": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "id": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "is": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "links": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "location": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "message": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "origin": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "parent": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "progress": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "label": "str",
        "maxLength": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "settings": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "type": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "visualizations": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      }
    }
  }
}
```
### `POST /simulations`

- Status: `skipped_mutating`
- Tested path: `/simulations`
- Reason: POST may mutate remote state; not executed by inventory test.
