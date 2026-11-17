# 本地 Home Assistant 容器（开发用）

用于本机验证 HA API、package 和 Lovelace 页面，不是生产部署。

## 容器

- 镜像：`ghcr.io/home-assistant/home-assistant:stable`
- 容器名：`espectre-plus-ha`
- 端口：`8123`
- 配置目录：放在仓库外（例如 `<HA_CONFIG_DIR>`），不要提交
- 时区：`Asia/Shanghai`

PowerShell 启动示例：

```powershell
$docker = (Get-Command docker).Source
$cfg = '<HA_CONFIG_DIR>'
& $docker run -d --name espectre-plus-ha --hostname espectre-plus-ha `
  --restart unless-stopped --stop-timeout 30 -p 8123:8123 `
  -e TZ=Asia/Shanghai -v "${cfg}:/config" `
  --log-opt max-size=10m --log-opt max-file=2 `
  ghcr.io/home-assistant/home-assistant:stable
```

首次启动打开 <http://127.0.0.1:8123> 完成 onboarding。管理员密码和长期 token 只写仓库外的私有交接文件，不写入仓库、README 或 Git。

## 验证

```powershell
Invoke-RestMethod http://127.0.0.1:8123/api/
```

带长期 token 访问：

```powershell
$headers = @{ Authorization = "Bearer $env:HA_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8123/api/config -Headers $headers
```

## 当前边界

- 容器已有 onboarding、API 和默认实体，但还没有 ESPHome/ESPectre 设备实体。
- `homeassistant/packages/espectre_plus.yaml` 依赖 `sensor.study_*`、`light.study_*` 等实体，设备接入前不要期待报表有数据。
- 真实 CSI 仍要 ESPectre Direct API，不是 HA 自带能力。
