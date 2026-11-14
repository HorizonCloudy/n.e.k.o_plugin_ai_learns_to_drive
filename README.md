# 学车助手（ai_learns_to_drive）

给《AI Learns To Drive》用的 N.E.K.O. 陪玩插件。它不注入游戏进程，主要读写游戏自己的存档（例外：`ald_run` 会启动游戏或给游戏窗口发键，见下）：

- `%APPDATA%\AI Learns To Drive\settings\local.settings`
- `%APPDATA%\AI Learns To Drive\evolution\*.evolution`

两个文件都是 **gzip + JSON**（已从游戏程序集和真实存档确认）。

## 能做什么

| 入口 | 用途 |
|---|---|
| `ald_status` | 游戏是否在跑、最新基因组、代数与最好成绩 |
| `ald_settings` | `get` 查看 / `set` 修改 / `preset` 套预设 / `recommend` 看建议 |
| `ald_genomes` | `list` 列表 / `inspect` 详情 / `trend` 训练曲线 / `mutate` 生成变异副本 |
| `ald_autopilot` | `start` 后监听游戏退出，读取训练曲线并自动调参 |
| `ald_run` | `status` / `launch` 启动游戏 / `toggle`·`start` 发 run_key（默认 F5）/ `stop` 发 stop_key（默认 Shift+F5） |

可调字段：`MutationRate`、`SelectionSize`、`UnitsCount`、`WeightDecay`、`TimeLimit`、`PreserveParentsSize`、算法编号、奖励 `Rewards`、`MaxPopulation2` 等。白名单之外的字段一律拒绝。

## 安全边界

- 每次写盘前自动生成 `*.bak-时间戳` 备份。
- 游戏运行时默认拒绝写设置（游戏退出时会用内存里的设置覆盖文件）。
- `allow_write = false` 可一键关掉所有修改（包括自动巡航在游戏退出后的自动调参）。
- `verify_game`（`auto` = 检测到游戏安装才开）：`ald_status` 报告安装目录、exe 和存档是否存在；开启时每次写盘后回读校验；`ald_run action=launch` 会等最多 15 秒确认进程出现，结果带 `running`。
- 自动巡航默认关闭，需要在 `config/plugin.toml` 里手动打开。

## 安装

1. N.E.K.O. 插件管理器 → 开发模式 → 加载未打包插件。
2. 选择本目录（目录名必须等于插件 ID `ai_learns_to_drive`）。
3. 校验 → 加载 → 启动 → 在入口点里触发 `ald_status`。

如果宿主要求源码树路径，把本目录放到 N.E.K.O 的 `plugin/plugins/ai_learns_to_drive` 即可。

## 已知限制

- `ald_run` 的 toggle/start/stop 会把游戏窗口切到前台并用 keybd_event 发键，按键由 config 里的 run_key/stop_key 决定；不模拟鼠标点击。
- `SelectionAlgorithm` / `CrossoverAlgorithm` 等枚举以游戏内的整数编号暴露，未做中文映射。
- 没有做交叉（crossover）算子；`mutate` 只做权重/偏置扰动。

## 自检

```powershell
python ald.py
```

会用一个临时目录验证读写、备份、校验、建议和变异逻辑。

## 更新记录（2026-11-13）

- 巡航写设置前重新检查游戏是否已重新打开，并统一走 `allow_write` 闸门；被拦下时记录 `skipped` 原因。
- 写盘失败不再推进 `_last_genome_mtime`：同一轮训练数据最多重试三次，之后跳过并记录。
- `MutationRate=0.0` 等合法零值不再被默认值顶掉，`recommend` 的基线读的是存档里的真实值。
- 巡航停止时会 `cancel()` 循环任务，避免再 start 出现两个循环重复写盘。
- 临时文件名带纳秒时间戳，不再共用同一个 `.tmp`。

## 更新记录（2026-11-14）

- 巡航被闸门拦下时同样不推进 `_last_genome_mtime`：游戏在轮询间隔里重新打开的，退出后下一轮会补上这轮调参；连续三次仍被拦才跳过。之前拦下即标记已处理，建议会永久丢失。
- 新增 `tests/test_cruise_gate.py`：覆盖拦下不推进、重试计数、三次放弃、游戏退出后成功应用。

