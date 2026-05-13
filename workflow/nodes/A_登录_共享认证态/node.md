# A_登录_共享认证态

## Role
- Workflow 前置节点。
- 建立并验证共享认证态，供后续所有 `wqb_core` CLI 节点复用。

## Upstream
- None

## Downstream
- `B_主题_平台机会`
- `C_金字塔现状`

## Inputs
### Necessary
- `wqb_core` 可执行环境
- 可用的认证来源：
  - 已缓存 cookie，或
  - `.env` / 显式账号密码

### Optional
- 已存在的 `.wqb_cli_auth/cookies.json`
- 本轮 run 根目录

## Outputs
### Necessary
- `00_auth/post_authentication.json`
- `00_auth/get_authentication.json`
- `00_auth/node_summary.md`
- 可复用的共享认证态：
  - `.wqb_cli_auth/cookies.json`

### Optional
- 认证返回中的用户权限信息

## Success Criteria
- 显式登录成功或现有共享认证态验证成功。
- 后续节点无需重新登录即可继续调用 `wqb_core` CLI。

## Failure Criteria
- 登录失败。
- 认证验证失败。
- 共享 cookie 未建立且不可复用。
