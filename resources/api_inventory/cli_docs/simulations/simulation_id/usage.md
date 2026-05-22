# CLI 用法: `/simulations/{simulation_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Simulation status/details.

## 查看定义

```powershell
python -m wqb_cli api show "/simulations/{simulation_id}"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/simulations/{simulation_id}" --var simulation_id=2UnwIe7g5jEcCgDvI4GpqO
```

实际执行:

```powershell
python -m wqb_cli api call GET "/simulations/{simulation_id}" --var simulation_id=2UnwIe7g5jEcCgDvI4GpqO
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
