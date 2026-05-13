# E_数据与字段可行性

## Role
- 把主塔落到 dataset / datafield 候选。
- 使用自己的池子 / 研究地图、`docs/data_all` 和插件分析数据，输出一批可用 datafield。

## Upstream
- `D_选主塔`

## Downstream
- `F_社区_帮助中心经验`
- `H_经济学机制假设`

## Inputs
### Necessary
- `D` 选出的主塔：
  - `region`
  - `delay`
  - `category`
- `docs/data_all/info_data.bin`
- `docs/data_all/all_data.pickle`
- 当前主塔 active alpha：
  - 通过 `filter_alphas --status ACTIVE --tag {region}/D{delay}/{category}`
- 筛选优先级：
  - OS 差的 dataset 不用
  - 已使用 datafield 不能再用
  - 已使用 dataset 最好不要再用

### Optional
- 插件 dataset / field 分析缓存
- 当前塔内 neutralization / universe 先验

## Outputs
### Necessary
- `04_E_data_and_field_feasibility/active_tower_alphas__{REGION}_D{DELAY}_{CATEGORY}__WQBRAIN.json`
- `04_E_data_and_field_feasibility/used_fields_by_alpha__{REGION}_D{DELAY}_{CATEGORY}.json`
- `04_E_data_and_field_feasibility/dataset_screening_step1__{REGION}_D{DELAY}_{CATEGORY}.json`
- `04_E_data_and_field_feasibility/available_datafields__{REGION}_D{DELAY}_{CATEGORY}.json`
- `04_E_data_and_field_feasibility/node_summary.md`

### Optional
- 已使用 dataset 集合
- 预筛后的 preferred datasets
- field 级统计特征

## Success Criteria
- 得到一批可直接进入后续研究的 candidate datafields。
- 已执行三层约束：
  - OS 差 dataset 排除
  - 已使用 datafield 硬排除
  - 已使用 dataset 尽量避开

## Failure Criteria
- 没先做 OS 筛选。
- 没排除已使用 datafield。
- 没产出正式 candidate datafield 库。
