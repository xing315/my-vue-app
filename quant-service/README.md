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
