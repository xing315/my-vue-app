# 量化分析服务

只读研究服务。盘中行情只更新价格；正式评分必须由盘后流水线写入
`data/latest-dashboard.json`。没有经过验证的快照时接口返回 `unavailable`，不会生成推荐。

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 首次生成真实数据

```sh
chmod +x run_pipeline.sh run_server.sh
./run_pipeline.sh
./run_server.sh
```

首次需要获取全 A 股近 900 天日线，可能持续较长时间。可先用
`./run_pipeline.sh --limit 50 --min-coverage 0.7` 验证环境，但限量快照不能代表全市场筛选。
采集默认绕过 macOS 系统 HTTP 代理；如果当前网络必须使用代理，请设置
`QUANT_USE_SYSTEM_PROXY=1` 后再运行。

Vite 将 `/api/quant` 代理至本服务。生产环境应由反向代理转发同一路径，并用定时任务在交易日收盘后运行 `./run_pipeline.sh`。

### Supabase 发布与 Mac 定时任务

1. 在 Supabase 执行项目迁移。
2. 复制 `.env.example` 为 `.env`，填入 `SUPABASE_URL` 和仅保存在 Mac 上的 Supabase Secret key（环境变量名继续使用 `SUPABASE_SERVICE_ROLE_KEY`）。
3. 执行 `./run_pipeline.sh`，校验通过的全市场快照会自动批量发布到 Supabase。
4. 执行 `./install_launch_agent.sh` 安装每日 16:45 任务。

日常同步会读取本地 Parquet 的最后交易日，只下载缺失日期。同步日志位于 `data/logs/`。

### DuckDB

`npm run quant:db:init` 会创建 `data/quant.duckdb`。`daily_bars`、`latest_spot`和
`latest_financial` 是直接读取 Parquet 的视图；股票信息、每日评分、同步记录和回测元数据保存在 DuckDB 实体表中。每次 `quant:sync` 会自动更新这些表。
