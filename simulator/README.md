# NAS / HA 联调预览

页面用于验证 NAS 端接口、房间看板和 CSI 波形。默认是 mock；配置 `ESPECTRE_CSI_URL` 后切换到 ESPectre Direct HTTP 的真实原始 CSI 流。房间数据仍是 mock，不能把整页当作 HA 整机验收。

## 结构

```text
simulator/
├── server.py              # HTTP 路由、CLI、provider 选择
├── mock_room.py           # 房间场景与功率/电量 mock
├── wifi.py                # MockWifi / EspCsiWifi，统一 /api/wifi 契约
├── csi_http.py            # Direct HTTP 客户端 + V8 二进制帧解析
├── fake_csi_device.py     # 本地假设备，仅用于协议联调
├── frontend/              # 页面、样式、Canvas 图表
└── tests/                 # 解析器、provider、HTTP 集成测试
```

HTTP 层只依赖 `/api/state`、`/api/control`、`/api/wifi`；房间和 CSI 各自是独立 provider。`csi_http.py` 不依赖页面，可单独复用。

## 本地启动

```powershell
# 默认 mock
.\.venv\Scripts\python.exe simulator\server.py --port 8080

# 真实设备：IP 以设备实际地址为准，不要提交到仓库
$env:ESPECTRE_CSI_URL = "http://<device-ip>:62587"
.\.venv\Scripts\python.exe simulator\server.py --port 8080
```

也可以直接传 `--csi-url http://<device-ip>:62587`。打开 <http://127.0.0.1:8080>。默认只监听本机。

## 没有 2.4 GHz 硬件时

```powershell
# 终端 1：生成与真实设备同格式的 V8 帧
.\.venv\Scripts\python.exe simulator\fake_csi_device.py --port 62587

# 终端 2：让预览服务读取假设备
.\.venv\Scripts\python.exe simulator\server.py --port 8080 --csi-url http://127.0.0.1:62587
```

假设备只验证二进制协议、重连和页面，不产生真实无线信道数据。页面来源会显示 `ESPectre CSI`，这是协议联调模式；不要把该截图当作现场实测。

## API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/state` | 房间状态、灯光、功率、电量、事件 |
| GET | `/api/wifi` | CSI 子载波、RSSI、底噪、波动指标、状态 |
| GET | `/api/health` | 服务状态和 WiFi 来源 |
| POST | `/api/control` | 房间控制，JSON 为 `{"action":"...","value":...}` |
| POST | `/api/wifi/burst` | 仅 mock 模式可注入模拟干扰；真实模式返回 409 |

`/api/wifi` 关键字段：

```json
{
  "source": "espectre",
  "source_label": "ESPectre CSI",
  "status": "streaming",
  "simulated": false,
  "channel": 6,
  "rssi_dbm": -48.0,
  "noise_dbm": -92.0,
  "interference_pct": 18,
  "fluctuation_pct": 18,
  "quality_pct": 82,
  "subcarriers": [0.12, 0.18, 0.30]
}
```

- `subcarriers` 为 64 个子载波的归一化 CSI 幅值，范围 0–1；真实模式来自 V8 帧 `sqrt(I² + Q²)`，再按帧峰值归一化。
- `fluctuation_pct` 是相邻帧归一化 CSI 形状变化的平滑值，用来观察信道扰动；`interference_pct` 保留为兼容字段。它不是绝对干扰功率，不能当作频谱仪测量值。
- `status` 为 `streaming`、`waiting`、`offline` 或 `stale`；真实模式没有数据时字段为 `null`，页面显示 `--`，不会用假值填充。
- `source` 为 `mock` 时页面显示“模拟 CSI”，并保留“模拟干扰”按钮；非 mock 时按钮隐藏。

## NAS 部署

以下命令在本机执行，`NAS_USER`、`NAS_HOST`、`PROJECT_DIR` 按实际环境替换；凭据不要写进仓库。

```powershell
tar -czf simulator.tgz --exclude='simulator/__pycache__' --exclude='*.pyc' simulator
ssh "$NAS_USER@$NAS_HOST" "mkdir -p '$PROJECT_DIR'"
scp simulator.tgz "$NAS_USER@$NAS_HOST:/tmp/simulator.tgz"
ssh "$NAS_USER@$NAS_HOST" "tar -xzf /tmp/simulator.tgz -C '$PROJECT_DIR' --strip-components=1"
```

systemd 设备地址放在权限受限的 `EnvironmentFile`，不要写进 unit：

```ini
[Service]
Type=simple
User=<NAS_UID>
WorkingDirectory=<PROJECT_DIR>
EnvironmentFile=-/etc/espectre-plus-sim.env
ExecStart=/usr/bin/python3 -B <PROJECT_DIR>/server.py --host 0.0.0.0 --port 8100
Restart=on-failure
RestartSec=3
```

```ini
# /etc/espectre-plus-sim.env, chmod 600
ESPECTRE_CSI_URL=http://<device-ip>:62587
```

没有该文件时服务保持 mock。服务只让局域网访问，不映射公网。修改后重启并检查：

```bash
curl -s http://127.0.0.1:8100/api/health
curl -s http://127.0.0.1:8100/api/wifi | head -c 500
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s simulator/tests -v
node --check simulator/frontend/app.js
```

## 边界

- 房间控制、功率和电量仍是 mock；真实 HA REST/WebSocket provider 尚未接入。
- 真实 CSI 需要 ESP32 已连 Wi-Fi、ESPectre sensing 正在运行，并打开 Direct API（默认端口 62587）。Direct API 要求允许的 `Origin`，`csi_http.py` 已固定发送 `https://espectre.dev`。
- 打开 `/espectre/v1/csi` 会暂停设备的运动检测事件；预览服务不要和关键生产自动化长期争用同一设备。
- 真实设备只放在可信局域网，不要把 Direct API 或 NAS 预览映射到公网。
