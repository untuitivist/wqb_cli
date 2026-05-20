# `/users/{user_id}/alphas`

- URL template: `https://api.worldquantbrain.com/users/{user_id}/alphas`
- Methods: `OPTIONS`
- Sources: `platform_dynamic_capture`
- Safe probe: `True`
- Description: Observed by passive platform network capture.

## Probe

- Skipped/Error: `Observed by platform dynamic network capture; no separate safe probe was run.`

## Dynamic Capture

### `OPTIONS /users/JL40454/alphas`

- Seen count: `14`
- Status codes: `200`
- Query keys: ``
- Content types: `application/json`

#### Response Shape

```json
{
  "actions": {
    "GET": {
      "author": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "classifications": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "color": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "competitions": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateCreated": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateModified": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateSubmitted": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "favorite": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "grade": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "hidden": {
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
      "name": {
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
      "os": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "osmosisPoints": {
        "label": "str",
        "maxValue": "int",
        "minValue": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "prod": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramidThemes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramids": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "children": "dict",
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
      "stage": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "tags": {
        "child": "dict",
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "team": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "test": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "themes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "train": {
        "child": "dict",
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
      }
    }
  }
}
```

## Endpoint Tests

### `OPTIONS /users/{user_id}/alphas`

- Status: `tested`
- Tested path: `/users/JL40454/alphas`
- HTTP: `200 OK`
- Elapsed: `675 ms`
- Content-Type: `application/json`
- Allow: `GET, HEAD, OPTIONS`

#### Tested Response Shape

```json
{
  "actions": {
    "GET": {
      "author": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "category": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "classifications": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "color": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "combo": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "competitions": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateCreated": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateModified": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "dateSubmitted": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "favorite": {
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "grade": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "hidden": {
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
      "name": {
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
      "os": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "osmosisPoints": {
        "label": "str",
        "maxValue": "int",
        "minValue": "int",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "prod": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramidThemes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "pyramids": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "regular": {
        "children": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "selection": {
        "children": "dict",
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
      "stage": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "status": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "tags": {
        "child": "dict",
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "team": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "test": {
        "child": "dict",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "themes": {
        "choices": "list",
        "label": "str",
        "readOnly": "bool",
        "required": "bool",
        "type": "str"
      },
      "train": {
        "child": "dict",
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
      }
    }
  }
}
```
