# 大金 G3 图片推送与摄像头

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/daikin-g3-media/)

契约 `daikin-g3-media-v1`，状态：已实现，未发布。适用于 BRY88BBA15G
社区 ESP32 固件和配套屏幕 MCU 固件。先查询 `capabilities.get` 和
`status.get`：屏幕能力 `MEDIA=0x400000`、`IMAGE=0x800000`、
`BINARY_LINK=0x1000000` 分别表示推送、图片组件和二进制串口支持。
旧 MCU 不显示相关管理控件，原有 SCN3 布局保持可用。

## 外部调用

复用 [HTTP 命令](device-http.md) 的 MessagePack 信封：

```python
import msgpack, urllib.request, uuid
body = msgpack.packb({"request_id": uuid.uuid4().hex,
    "action": "screen.push.send", "params": {"id": 1001,
    "title": "门口有人", "text": "请查看摄像头", "mode": "timed",
    "duration_ms": 10000, "wake": True}}, use_bin_type=True)
req = urllib.request.Request("http://device/api/v1/command", body,
    {"Content-Type": "application/msgpack"})
reply = msgpack.unpackb(urllib.request.urlopen(req).read(), raw=False)
```

设置管理密码的设备须附加现有的管理员 Basic 或会话鉴权。MQTT 使用
`phicomm/v2/<scope>/daikin/<device_id>/command` 和对应 `/result`，相同信封、
MessagePack、非 retained，权限取决于既有 broker/账户 ACL。
已配对 openiot UDP v4 的 CONTROL 权限可调用媒体/推送命令、查询及流启停；
`screen.link.set`、`screen.stream.set` 需要 ADMIN，通过 HTTP/MQTT 管理入口配置。
UDP 配对和传输格式沿用现有实现。

写请求返回 `code:"accepted"` 和 `data.request` 串口序号。轮询
`screen.media.get`，仅在 `request.sequence` 匹配、`state:"complete"`、
`result:0` 时表示 MCU 接受操作。通知是否已显示/已确认应检查 `messages`。
同一时刻只有一个串口写请求；`busy` 可稍后重试。`uncertain` 或 MCU 重启时
先查询状态，再决定重试。使用非零 uint32 ID；保留在队列/最近十六条历史中的
相同 ID 和相同内容不重复播放，相同 ID 改内容会被拒绝。重启清空去重历史。

| 命令 | 参数和行为 |
| --- | --- |
| `screen.media.begin` | `id,total,crc32,width,height`，均为 uint；分配临时图片槽 |
| `screen.media.chunk` | `id,offset,bytes`；连续偏移，`bytes` 为最多 512 字节的 Base64；相同偏移/内容可重传 |
| `screen.media.commit` | `id`；完整长度、CRC32、JPEG 格式及尺寸校验 |
| `screen.media.cancel` | `id`；释放未被通知引用的图片 |
| `screen.media.get` | 无参数；上传偏移、图片槽、队列历史、请求结果、像素 CRC |
| `screen.push.send` | `id` 必填；其余见下表 |
| `screen.push.get` | 无参数；同媒体状态 |
| `screen.push.dismiss` | `id`；关闭活动或排队的通知 |
| `screen.push.select` | `index:0..4`；选择原页面或前四条通知之一 |

| 推送字段 | 约束/默认值 |
| --- | --- |
| `image_id` | 已提交的图片 ID，默认 0；可与文字组合 |
| `title`,`text` | UTF-8，分别最多 64/512 **字节**；正文允许换行；图片、标题、正文至少一项非空 |
| `mode` | `timed`（默认）或 `confirm` |
| `duration_ms` | 定时模式 1..3600000，默认 10000；从实际亮屏显示开始计时，OTA 暂停期间不计时 |
| `wake` | 默认 true；黑屏时临时亮屏；false 时等待屏幕自然亮起 |
| `brightness` | 临时请求亮度 1..100%，默认 30%，仍受硬件/用户亮度上限限制 |

队列容量 **16 条**，包含正在显示的一条，图片缓存仍限 **4 张**。前四条通知
以圆角卡片堆叠显示；在 350 毫秒内双击前面触摸键，按 **0（原页面）→ 1 → 2 →
3 → 4 → 0** 循环，跳过不存在的通知页。切换时保留消息，未显示通知的计时暂停。
前面的通知消失后，后续队列自动补入前四条。单击等待双击判定结束后确认当前
通知，按键被消费，不切换原页面；长按保留原关机行为。第 0 页恢复原页面及亮屏
策略。远程可调用 `screen.push.select {"index":0..4}` 选择同一展示页。
`screen.push.get` 返回 `view_index`、`queued`、`queue_capacity`（16）、
`image_capacity`（4）、`stack_capacity`（4）、完整 `queue` 和最近 16 条 `messages`。
状态为 `queued/displayed/confirmed/timedout/dismissed/failed`。
图片最多四张，每张 128 KiB、1..480 × 1..854；仅存 SDRAM，未被引用的图片
120 秒过期，MCU 重启清空。解码失败标为 failed，继续下一条。

调用端须先缩放和压缩。仅支持 8 位基线顺序 JPEG、三分量 YCbCr、常见
4:4:4/4:2:2/4:2:0 采样及单次扫描；不接受 progressive、灰度、CMYK、重启间隔。
WebUI 在浏览器处理 PNG/JPEG/WebP；CLI 使用 Pillow：

```sh
python3 -m pip install msgpack Pillow
python3 BRY88BBA15G/tools/screen_media.py prepare --image photo.png --width 320 --height 240 --output push.jpg
python3 BRY88BBA15G/tools/screen_media.py --url http://device push --image photo.png --title '快递到了' --mode confirm
python3 BRY88BBA15G/tools/screen_media.py --url http://device get push
```

`IOTCLOUD_AUTH` 可提供已有的 `admin:密码`。CLI 自动等待每次 MCU 回执。

## 摄像头拉流

`screen.stream.set` 参数：`url` 必填（最多 383 字节），`username/password`
各最多 63 字节，`width` 默认 320（1..480）、`height` 默认 240（1..854）、
`fps` 默认 1（1..10）、`enabled` 默认 true、`verify_tls` 默认 true。
HTTP/HTTPS URL 支持路径中的 `{width}/{height}/{fps}`；不支持 URL 内嵌凭据、
IPv6 字面量、片段或重定向。省略 password 保留原密码，传空串清除。
配置保存在 ESP NVS；查询只返回 `password_set`，不返回密码。
发送 `url:"",enabled:false` 可清除摄像头地址及凭据；清除后须先配置有效地址才能启动。

```python
{"action":"screen.stream.set", "request_id":"camera-1", "params":{
 "url":"http://camera/mjpeg?w={width}&h={height}&fps={fps}",
 "width":320,"height":240,"fps":1,"enabled":True,"verify_tls":True}}
```

屏幕 MCU 组装 HTTP 请求，处理 Basic / Digest MD5（qop=auth 或旧式无 qop）、
multipart MJPEG、HTTP chunked 及单 JPEG 响应，校验并通过硬件解码为 RGB565。
ESP32 只提供有流控的 DNS/TCP/TLS 字节透传。源端实际帧尺寸须不大于请求尺寸；
URL 参数是否生效取决于源服务。`fps` 是请求上限，实际帧率取决于 JPEG 大小、
串口速率和 MCU 绘制耗时。MCU 按设定间隔跳过过快帧；源服务应按设备可持续的
帧率输出，避免 TCP 缓存使画面延迟。可从默认 1 FPS 开始，依据 `get` 的实际帧率调整。
RTSP/H.264 摄像头需先由摄像头服务器转为指定尺寸的 MJPEG。

在“屏幕→服务→摄像头”配置地址，点击“添加摄像头页面”，保存布局。
新页面使用完整 4×6 网格，原页面保留；也可添加图片组件并选择 contain/cover。
SCN3 仍为 9520 字节，组件 `type=8`，组件内偏移 86/87 分别为
`image_source=0` / `image_fit=0 contain,1 cover`。最多八页、32 组件。

仅在图片组件所在页面可见、屏幕亮起、无推送遮挡及无 OTA 时拉流。
隐藏/休眠立即关闭连接；失败按 1..30 秒退避。`screen.stream.start/stop`
无参数，持久化启停状态；`get` 返回配置及 `state`（off/paused/connecting/
reading/backoff）、frames、dropped、bytes、实际尺寸/帧率、像素 CRC 和错误码。
默认校验 TLS 证书；测试自签名源可显式关闭校验。

## 串口速率与恢复

`screen.link.get` 返回配置、实际速率、会话、CRC/帧错误、重传与回退计数。
其中 `framing` 细分超时与格式错误，并报告最近错误的帧长度、声明长度及头部是否有效。
`set` 接受 `mode:"fixed"|"auto"`、`rate`、`max_rate`、`apply_now`。
支持 115200、230400、460800、921600；默认固定 115200。auto 从上限向下尝试。
切换仅发生在 MCU 恢复阶段：清空发送、旧速率 READY、新速率 CRC 探测、双向确认；
超时回退 115200。`apply_now:true` 重启屏幕 MCU 进入恢复协商；否则下次恢复生效。
高波特率持有 ESP APB/禁轻睡眠锁；正常运行不自行升速，单端重启会重新同步。

新增二进制帧使用零分隔及转义：`00 → DB DC`、`DB → DB DD`。
未转义内容为 `"GM",version=1,channel,u32LE session,u32LE sequence,u16LE length,`
`payload,CRC32LE`；CRC 覆盖头和载荷，载荷最多 640 字节。
通道为 link=0、command=1、reply=2、socket=3、socket_ack=4、socket_event=5。
图片和 TCP 块最多 512 字节，单块确认/有限重试；session 隔离重启前数据，
sequence 和内容校验处理重复。工厂 OTA 独占原始串口。
错误码：0成功、1范围、2忙、3不存在、4 CRC、5格式、6解码、7离线。

规范常量见 [机器可读契约](contracts/daikin-g3-media-v1.json)。

媒体操作码为 begin=1、chunk=2、commit=3、cancel=4、push=5、dismiss=6、
query=7、stream_config=8、stream_start=9、stream_stop=10、select=11。
select 的操作码后带一个 u8 展示页号。媒体状态版本 2 长 324 字节，后接 40 字节
流状态：32 字节头、4 个 17 字节图片记录、16 个 9 字节队列记录（u32 id、
u32 image_id、u8 state）、16 个 5 字节历史记录（u32 id、u8 state）。
头的字节 22/23 为展示页/队列数，24/25 为 JPEG SR / 右移 10 位的 IR 标志，
26..27 为解码耗时毫秒（u16LE），28..31 为消息/图片/展示页容量及状态版本。
其后可附加 64 字节解码诊断（16 个 LE32）：SR、IR、CR、CFG、码流地址、输出
地址、CODLEN、CLKEN1、PRSTR1、前两个 RGB565 像素、前 512 字节像素 CRC32、
启动前 SR、启动前 IR、耗时、扫描数据 CRC32、扫描偏移。
ESP 在分步升级期间也接受早期 172 字节和无诊断扩展的 364 字节状态快照。
