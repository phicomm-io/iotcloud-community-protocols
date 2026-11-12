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
UDP 配对和传输格式沿用现有实现。UDP v4 的完整帧最多 1200 字节，内部
MessagePack 命令体最多 1024 字节；长 URL、正文和鉴权字段合并超出此限制时，
请使用 HTTP 或 MQTT。各字段的单独上限仍适用。

写请求返回 `code:"accepted"` 和 `data.request` 串口序号。轮询
`screen.media.get`，仅在 `request.sequence` 匹配、`state:"complete"`、
`result:0` 时表示 MCU 接受操作。通知是否已显示/已确认应检查 `messages`。
同一时刻只有一个串口写请求；`busy` 可稍后重试。`uncertain` 或 MCU 重启时
先查询状态，再决定重试。使用非零 uint32 ID；保留在队列/最近十六条历史中的
相同 ID 和相同内容不重复播放，相同 ID 改内容会被拒绝；仍在队列中的同地址
通知按下文续时规则处理，可使用原 ID 更新内容和选项。重启清空去重历史。

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
`payload,CRC32LE`；CRC 覆盖头和载荷，载荷最多 1152 字节。
通道为 link=0、command=1、reply=2、socket=3、socket_ack=4、socket_event=5。
图片和 TCP 块最多 512 字节，单块确认/有限重试；session 隔离重启前数据，
sequence 和内容校验处理重复。工厂 OTA 独占原始串口。
错误码：0成功、1范围、2忙、3不存在、4 CRC、5格式、6解码、7离线。

规范常量见 [机器可读契约](contracts/daikin-g3-media-v1.json)。

媒体操作码为 begin=1、chunk=2、commit=3、cancel=4、push=5、dismiss=6、
query=7、stream_config=8、stream_start=9、stream_stop=10、select=11、push_url=12。
select 的操作码后带一个 u8 展示页号。地址推送需能力位 25（33554432）：
16 字节原推送头后接 519 字节现有图源配置，再接标题和正文；image_id 必须为 0。
媒体状态版本 3 长 352 字节，后接 44 字节流状态：44 字节头、4 个 17 字节图片记录、
16 个 10 字节队列记录（u32 id、u32 image_id、u8 state、u8 地址图源标志）、
16 个 5 字节历史记录。头字节 22/23 为展示页/队列数，24/25 为 JPEG 标志，
26..27 为解码耗时毫秒（u16LE），28..31 为容量/版本；偏移 32/36/40 的 LE32
依次为合并后的最近推送 ID、图源错误、当前剩余毫秒。流状态偏移 40 为通知 ID（0 为页面）。
其后可附加 64 字节解码诊断（16 个 LE32）：SR、IR、CR、CFG、码流地址、输出
地址、CODLEN、CLKEN1、PRSTR1、前两个 RGB565 像素、前 512 字节像素 CRC32、
启动前 SR、启动前 IR、耗时、扫描数据 CRC32、扫描偏移。
ESP 在分步升级期间也接受早期 172 字节及 v2 的 364/428 字节状态快照。

## 临时图片 / 视频流通知

`screen.push.send` 增加 `url`、`username`、`password`、`width`、`height`、`fps`、
`verify_tls`，图源规则与 `screen.stream.set` 相同。仅地址也可推送，按 HTTP 响应
自动识别 JPEG 或 MJPEG；图源需提供指定分辨率，支持 `{width}`、`{height}`、
`{fps}` 占位符，MCU 负责解码和适配显示。`image_id` 必须省略或为 0。
凭据默认空，仅保留在临时队列内。

```json
{"action":"screen.push.send","params":{"id":2001,"title":"检测到动作",
 "url":"http://camera/mjpeg?width={width}&height={height}&fps={fps}",
 "width":320,"height":240,"fps":1,"duration_ms":20000,"wake":true}}
```

通知覆盖当前页面，首帧显示成功后才开始倒计时；可见期间 15 秒仍无首帧则标记失败，
继续后续通知。同一完整地址仍在队列中时，再推送会将剩余时间延长至至少本次指定值，
更新文字和选项，并在 `screen.media.get.last_push_id` 返回原通知 ID。图源选项不变
时复用连接，16 条队列已满也能续时。关闭通知使用该 ID；通知结束后的新事件应换新 ID。
同一串口序号的传输重试保持幂等，不重复续时。

页面与通知共用一个网络连接及 JPEG/RGB 缓冲；关闭、到时或选回展示页 0 后恢复原页面图源。
`screen.stream.get` 通过 `role`、`notification_id` 说明实际接收者，配置字段仍为
已保存的页面配置。通知图源不修改持久配置，也不占用 4 张上传图片缓存。

## 按推送 ID 更新

创建通知时由调用端指定非零 `uint32` 的 `id`，保存回执状态中的
`last_push_id`（同地址合并时返回实际保留的 ID）。支持 `update_supported:true`
的设备可调用 `screen.push.update`。它要求 `id` 和至少一个推送字段；
**只修改传入字段**，保留队列位置、当前展示页及未传入的图文内容。
已结束或不存在的 ID 返回 MCU `result:3`，不会创建或重播通知。

```python
# 只更新正文；原图片或流继续显示
{"action":"screen.push.update","params":{"id":2001,"text":"门口仍有活动"}}
# 从当前时刻起至少再显示 15 秒，重复调用不会缩短时间
{"action":"screen.push.update","params":{"id":2001,"duration_ms":15000}}
# 替换图源；其他显示选项保留
{"action":"screen.push.update","params":{"id":2001,"url":"http://camera/new.jpg"}}
# 主动关闭（活动、隐藏或排队中的消息均可）
{"action":"screen.push.dismiss","params":{"id":2001}}
```

`title/text` 可传空串清除；清除后至少须保留文字或图源。`image_id` 可替换已提交
图片，0 表示移除媒体；`url` 可替换图片/视频流地址，空串表示移除媒体。
`image_id` 与 `url` 不可同时传入。更换 URL 时省略的用户名、密码清空，避免把
旧凭据发给新图源；只更新分辨率、帧率或凭据时须已有 URL 图源。
同一 URL 不变且配置不变时，更新文字或时长保持 TCP 连接。
换图源从新画面实际呈现后继续计时；更新隐藏消息不会亮屏或抢占当前通知。

`duration_ms` 将剩余可见时长延长至至少所给值（1..3600000）；不缩短。
`mode:"confirm"` 切换为等待触摸确认，`mode:"timed"` 继续定时。其他字段与
`send` 的范围相同。`send` 保留创建时的重试去重语义，改内容应使用 `update`；
网络 `request_id`、UART 回执序号和通知 `id` 是不同标识。操作仍须等待匹配的
MCU 回执。能力位 26（67108864）表示更新支持；旧 MCU 返回 `unsupported`。

更新 UART 包沿用 PUSH 的前 16 字节，操作码为 13，随后为 LE16 字段掩码，
位 0..13 依次为 title、text、image_id、mode、duration_ms、wake、brightness、
url、username、password、width、height、fps、verify_tls。只要源字段中任一位
存在，就附加完整 519 字节源配置，其后按标题长度附加 UTF-8 标题/正文；
只合并掩码指定的字段，保留位必须为零。最大 1113 字节，帧上限仍为 1152。

```sh
python3 BRY88BBA15G/tools/screen_media.py --url http://device update 2001 --text '门口仍有活动' --seconds 15
```

通知层复用卡片、标题、正文和图片对象；修改文字或队列状态仅刷新相应区域。
通知遮挡业务页时暂停其内容计算，返回第 0 页时更新至最新数据。

## 过期与队列满策略

能力 `policy_supported:true`（位 27）支持 `ttl_ms` 和 `overflow`。`ttl_ms` 为接收起的硬过期时间，0 关闭，范围 0～86400000 毫秒；排队、隐藏、等待确认和维护暂停时仍计时。它与实际显示时长 `duration_ms` 独立，任何一个到期都会结束通知。`update` 传入 `ttl_ms` 会从本次接收起重新计时，可缩短或关闭；不传则保留。同地址 `send` 合并时 TTL 只延长。

```json
{"action":"screen.push.send","params":{"id":3001,"text":"门口运动","duration_ms":15000,"ttl_ms":30000,"overflow":"drop_oldest"}}
{"action":"screen.push.update","params":{"id":3001,"ttl_ms":10000}}
```

| `overflow` | 队列满时 |
| --- | --- |
| `reject`（默认） | 拒绝，返回 busy，不更改队列或留下去重记录，可稍后重试 |
| `drop_newest` | 主动丢弃新消息，MCU 回执成功，历史状态为 `dropped` |
| `drop_oldest` | 淘汰最早的等待消息并接收新消息；保护当前项，淘汰项为 `evicted` |

策略作用于新通知；同 ID 更新、原请求重试和同地址续期先于容量检查。淘汰只释放队列引用，上传的图片仍可复用，未引用图片按原有两分钟规则回收。

`queue[].expires_in_ms` 返回剩余硬过期毫秒数（0 表示未启用），硬过期记为 `expired`，显示时长结束仍为 `timedout`。历史最多 16 条，去重保留窗口也受此限制；应用应给新事件使用新 ID，更新只对仍在队列中的 ID 生效。通知及策略不跨 MCU 重启保存。

UART 扩展 `MEDIA_PUSH_POLICY=14` 的前 16 字节沿用 PUSH，随后为 TTL LE32、overflow 字节和 URL 标志；可选 519 字节图源配置后跟标题/正文。`MEDIA_PUSH_UPDATE` 掩码位 14 表示 TTL，在原 18 字节头后附 LE32，然后才是可选图源和文字。状态版本 4 的队列项由 10 字节增至 14 字节，末尾附剩余 TTL。新 ESP 仍转换读取旧版状态，不支持能力位时拒绝新选项。

## 运动检测接入例程

Frigate 的 `frigate/<camera>/motion` MQTT 事件、Scrypted MotionSensor 脚本或 MQTT 插件均可触发 webhook 桥。服务器用 go2rtc/FFmpeg 按需生成 320×240、1 fps MJPEG，运动时更新同一 ID，停止后由 TTL 结束。完整的容器、Home Assistant 自动化和 Scrypted 脚本见固件仓库的 [中文教程](https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/BRY88BBA15G/docs/motion-notifications.zh.md)。
