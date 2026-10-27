# Windows NAS 经 EasyTier 访问

记录日期：2026-10-25。版本一律是 EasyTier **2.6.4**（`2.6.4-8428a89d`）。

目标：Windows 上的机械硬盘给手机随时看文件、播影片。蜂窝网走 SMB 又慢又容易连不上，所以文件入口改成只绑在虚拟网卡上的 HTTP 服务。以后的移动端 App 是这条 HTTP 的套壳，自己负责连上 EasyTier，再美化浏览和播放。

## 拓扑

```text
手机 (android-phone, DHCP, 曾分配 10.144.144.20)
   |  同一 Wi‑Fi：局域网直连，不经过 EasyTier
   |  蜂窝：优先 IPv6 直连；打洞失败则经腾讯云转发
   v
Windows (win-nas, 10.144.144.10/24, 计算机名 Ptking-pc)
   ^
   |  发现 + 打洞失败时的加密转发
腾讯云 81.71.32.142  (SSH: root@81.71.32.142，别名 pigtalk 的用户 rossetta 不能登录)
```

虚拟网段 `10.144.144.0/24`。中继和两端用同一个网络名 `rossetta`。网络密钥、各端 X25519 私钥只留在下面这些文件里，不要抄进仓库：

| 位置 | 内容 |
|------|------|
| 云 `/etc/easytier/config.toml` | 中继身份、安全模式密钥、监听 |
| 云 `/etc/easytier/relay_x25519.pem`、`relay.secret` | 早期生成的密钥材料，权限 600 |
| Windows `C:\EasyTier\config\nas.toml` | Windows 节点配置 |
| 本机 `~/Downloads/easytier-android.toml` | 给手机导入的配置，已拷到 Windows `G:\Download` |
| 本机 `~/Downloads/deploy-easytier-nas.ps1` | Windows 一键部署脚本，PowerShell 5.x 语法 |

中继公钥（给客户端锁定用，不是私钥）：`9pk2IYUXT/3MjpONmOZSOeZgUQ0W3k0309WyPtxgXWw=`

最初想让云只做「另一个网络名的私有共享节点」。2.6.4 上这样握手失败（`local public key is not set`、`local private key is not set`）。云后来改成加入 `rossetta`，并写上固定的 `local_private_key` 和 `local_public_key`。云因此也在这个虚拟网里。

## 各端现状

**腾讯云**

- Debian，`easytier-core` 在 `/usr/sbin/easytier-core`，安装目录还有 `/opt/easytier`。
- systemd 服务名 `easytier`，开机自启。官方安装脚本另外生成过 `easytier@default`，已停用。
- 监听 `tcp/udp 0.0.0.0:11010` 和对应的 IPv6。
- 系统 `ufw` 原本只放行 22 和 3000。已加 `11010/tcp`、`11010/udp`（含 v6）。腾讯云安全组侧用户确认当时已放行。
- 安全模式开启。`relay_network_whitelist = "rossetta"`。

**Windows**

- 安装在 `C:\EasyTier`。计划任务 `EasyTier-NAS`，开机启动。
- 静态虚拟 IP `10.144.144.10`。主机名 `win-nas`。局域网地址 `192.168.31.240`，网卡名「以太网」。
- 部署脚本会在任务参数里带上 `--secure-mode` 和本机密钥。2.6.4 只在 toml 里写 `secure_mode.enabled = true`、不写本机私钥时，会报 `local private key is not set`。
- 已有公网 IPv6，前缀 `2408:8256:328f:9c0::/64`（路由通告和 DHCPv6）。`fe80` 不算。
- 共享名是 `机械硬盘`，不是 `NasShare`。手机必须用 `smb://10.144.144.10/机械硬盘`。`\\Ptking-pc\...` 只在家里局域网能解析。

**Android**

- 官方 `app-arm64-release.apk`（v2.6.4）。
- 主机名 `android-phone`，`dhcp = true`，不要占用 `10.144.144.10`。
- 必须有自己的 `local_private_key` / `local_public_key`，并锁定中继公钥。

## 路径和速度

同一 Wi‑Fi：手机和电脑在 `192.168.31.0/24`，SMB 走局域网，不经过虚拟网。

蜂窝、只有 IPv4 时：手机是对称 NAT，Windows 是端口受限 NAT，打洞失败。文件经腾讯云转发，大约几百 KB/s，和轻量服务器带宽一致。中继上的收发字节会成对出现（Windows 发出的量约等于云转给手机的量）。

打开 IPv6 之后：Windows 上 `easytier-cli route` 里，`android-phone` 的 `next_hop_hostname` 为 `DIRECT`，`path_len = 1`，延迟约 80ms。右边 `next_hop_hostname_lat_first` 仍是 `tx-relay-81-71-32-142`，两跳，延迟约 40ms。2.6.4 的 `latency_first` 默认是 false，实际走左边的直连。右边那条只是延迟更低的备选，带宽受云限制，不要为了那 40ms 改走中继。

向 `10.144.144.20` 发 ping 会超时。手机虚拟网卡不回应 ICMP。路由表里的延迟才是隧道通不通的依据。

80ms 上用 SMB 翻目录很慢。大文件整段拷贝才反映隧道带宽。直连上限是家里宽带的上行。KCP（`--enable-kcp-proxy`，Android 配置里 `enable_kcp_proxy = true`）只在直连丢包、大文件仍然只有几百 KB/s 时再开。是否已经打开，以两边当前配置为准。

## SMB 防火墙

Windows 防火墙按网卡是「公用 / 专用」分别放行 445。曾经看到：只有 Public 的「文件和打印机共享 (SMB-In)」是启用的，专用网络和域网络是关的。EasyTier 网卡经常被划成专用网络，蜂窝过来的 SMB 会在进系统前被丢掉，所以同一 Wi‑Fi 仍正常。

建议过的规则是只允许这些来源：

- `10.144.144.0/24`
- `192.168.31.0/24`

不要把 445 的远程地址设回 `Any`。这台电脑有公网 IPv6。是否已按这个范围改过，以当前防火墙规则为准。

## HTTP：HFS 3

蜂窝上的浏览和播片用 HTTP，不用 SMB。选了 HFS 3（[hfs.rejetto.com](https://hfs.rejetto.com/)）。手机用浏览器打开，管理页也是网页。

监听必须是虚拟网 IP，这样局域网和公网 IPv6 都连不上：

```yaml
port: 8080
listen_interface: 10.144.144.10
open_browser_at_start: false
```

`port` 以实际 `config.yaml` 为准。配置文件和 `hfs.exe` 在同一目录。保存后 HFS 会重载。

管理页里的 Listen interface 会把「这次连接没用到的地址」灰掉，并提示若地址是禁用的，先通过该地址连上再选。先用任意地址监听，浏览器打开 `http://10.144.144.10:端口/~/admin`，再选中 `10.144.144.10`。绑定之后不能再用 `localhost` 进管理页。改监听前 EasyTier 必须已经在运行，否则这个地址不存在。

`hfs.exe` 是控制台程序。直接当任务启动会弹出黑窗口，关掉窗口进程就没了。计划任务不要指向 `hfs.exe`，用 `wscript.exe //B` 跑一个 `start-hfs.vbs`，窗口样式 0。以当前登录用户、在登录时启动，不要用 SYSTEM 去读用户目录里的程序，否则会「无法打开」。启动前 `WScript.Sleep` 约 20 秒，等 `10.144.144.10` 出现。任务名按上次脚本是 `HFS3`。这一步用户报过「无法打开」，改为用户登录启动后是否成功，还没确认。

手机入口：`http://10.144.144.10:端口`。账号在 HFS 管理页里建。

## 以后的 App

套壳，不重做文件协议。

1. App 自己把 EasyTier 隧道拉起来（Android 现成核心是 2.6.4 的 arm64 构建）。隧道没起来之前，不出现文件界面。
2. 隧道之上只访问 `http://10.144.144.10:端口`。列表、下载、影片拖动播放都走 HTTP Range，不走 SMB。
3. 界面要补上 HFS 网页没有的操作：记住库地址、断线后自动重连隧道、目录和播放进度、蜂窝网上少次请求多拿数据。80ms 延迟下，按 SMB 的方式逐个请求小文件会卡。
4. 服务继续只绑 `10.144.144.10`。App 不把 445 或 HFS 端口暴露到公网。
5. 同一 Wi‑Fi 可以仍走局域网；蜂窝必须走虚拟 IP。主机名 `Ptking-pc` 在虚拟网里没有用。
6. 同时只能有一个 VpnService。用户如果还开着别的 VPN，EasyTier 起不来。
7. 直连失败时流量会经 `81.71.32.142` 转发，速度和云的带宽、流量包绑在一起。界面上要能看出当前是 `DIRECT` 还是经 `tx-relay-81-71-32-142`，避免把「几百 KB/s」当成磁盘或 App 的问题。
