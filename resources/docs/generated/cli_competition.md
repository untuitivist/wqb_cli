# WQB Competition CLI

`wqb competition` 封装 competition 接口。

已覆盖：

- `wqb competition list`
- `wqb competition get <competition_id>`
- `wqb competition agreement <competition_id> --method GET|POST`
- `wqb competition leaderboard <identifier> [--scope competition|consultant] [--board-type leader] [--method GET|OPTIONS]`
- `wqb competition guidelines <competition_id>`
- `wqb competition faq <competition_id>`
- `wqb competition spc submissions`
- `wqb competition spc submission-history <submission_id>`
- `wqb competition spc submission-options [submission_id]`
- `wqb competition spc create-submission --input <json>`
- `wqb competition spc update-submission <submission_id> --method PUT|PATCH --input <json>`

排行榜命令有两个通用 scope：`competition` 调用 `/competitions/{competition_id}/boards/{board_type}`，`consultant` 调用 `/consultant/boards/{board_type}`。SPC 是 consultant scope 下的 `board_type=spc`，不是代码中的特殊排行榜。Guidelines 读取 competition agreement，FAQ 从 competition detail 中提取 URL。

安全策略：agreement 的 `POST`、SPC create/update 都会直接发送远端变更请求；只读命令不会隐式执行这些操作。

完整 endpoint 到命令映射见 `api_inventory/BUSINESS_CLI_COVERAGE.md`。
