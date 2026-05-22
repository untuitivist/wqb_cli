# WQB Platform CLI

`wqb platform` 封装平台杂项只读接口。

已覆盖命令:

- `wqb platform achievements`
- `wqb platform achievement-icon ALPHA_PERF_EXCELLENT`
- `wqb platform agreements`
- `wqb platform captcha`
- `wqb platform messages`
- `wqb platform tags`
- `wqb platform teams`
- `wqb platform video-courses`
- `wqb platform competition-level-icon none`

验证记录:

- 所有命令已完成参数检查。
- 实际调用已执行；当前平台真实状态包括 `captcha=200 OK`，部分平台内容返回 `401/404/405`。
