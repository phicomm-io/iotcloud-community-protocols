# Daikin G3 media push and camera

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/daikin-g3-media/)

Contract `daikin-g3-media-v1`: implemented, unreleased. Requires the BRY88BBA15G
community ESP32 firmware and matching screen MCU firmware. Query
`capabilities.get` and `status.get`: screen capabilities `MEDIA=0x400000`,
`IMAGE=0x800000`, `BINARY_LINK=0x1000000` indicate push, image components and
binary UART support. Older MCUs retain their SCN3 layout; unsupported controls
are hidden.

## External API

Use the existing [HTTP command](device-http.md) MessagePack envelope:

```python
import msgpack, urllib.request, uuid
body = msgpack.packb({"request_id": uuid.uuid4().hex,
    "action": "screen.push.send", "params": {"id": 1001,
    "title": "Someone at the door", "text": "Check the camera", "mode": "timed",
    "duration_ms": 10000, "wake": True}}, use_bin_type=True)
req = urllib.request.Request("http://device/api/v1/command", body,
    {"Content-Type": "application/msgpack"})
reply = msgpack.unpackb(urllib.request.urlopen(req).read(), raw=False)
```

When an administration password is configured, include existing admin Basic or
session authentication. MQTT uses
`phicomm/v2/<scope>/daikin/<device_id>/command` and `/result`, the same envelope,
MessagePack, no retain, and existing broker/account ACLs. Paired openiot UDP v4
CONTROL sessions may call media/push, queries and stream start/stop.
`screen.link.set` and `screen.stream.set` require ADMIN through HTTP/MQTT.
UDP pairing and framing follow the existing implementation.

Writes return `code:"accepted"` and UART sequence `data.request`. Poll
`screen.media.get` until matching `request.sequence`, `state:"complete"` and
`result:0`. Check `messages` for actual display/confirmation state. Only one UART
write is pending at a time; retry `busy` later. After `uncertain` or an MCU reboot,
query state before retrying. IDs are nonzero uint32. Identical ID/content still
in the queue or last eight history entries does not replay; changed content
under the same ID is rejected. Reboot clears deduplication history.

| Command | Parameters and behavior |
| --- | --- |
| `screen.media.begin` | `id,total,crc32,width,height`, all uint; allocate a transient image slot |
| `screen.media.chunk` | `id,offset,bytes`; contiguous offset; Base64 for at most 512 bytes; identical chunks can be retried |
| `screen.media.commit` | `id`; verify length, CRC32, JPEG format and dimensions |
| `screen.media.cancel` | `id`; release an image unreferenced by a notification |
| `screen.media.get` | No parameters; upload offsets, slots, history, request result, pixel CRC |
| `screen.push.send` | Required `id`; other fields below |
| `screen.push.get` | No parameters; same media snapshot |
| `screen.push.dismiss` | `id`; dismiss an active or queued notification |

| Push field | Limit/default |
| --- | --- |
| `image_id` | Committed image ID, default 0; may accompany text |
| `title`,`text` | UTF-8, at most 64/512 **bytes**; body permits newlines; image, title or body must be present |
| `mode` | `timed` (default) or `confirm` |
| `duration_ms` | Timed mode 1..3600000, default 10000; starts when actually visible; OTA suspension does not count |
| `wake` | Default true; temporarily wake a dark screen; false waits for natural wake |
| `brightness` | Temporary request 1..100%, default 30%, subject to hardware/user ceiling |

Sixteen FIFO entries including the active notification, with at most four image
slots. The first four notifications form a stack of rounded cards. Double-tap
the front capacitive button within 350 ms to cycle **0 (the original page),
1, 2, 3, 4, 0**; absent views are skipped. Switching keeps all notifications and
pauses their visible timers. The next queued message joins the stack when an
earlier notification disappears. A single tap confirms the selected notice
after the double-tap window and consumes that press. Original page and display
policy resume at view 0. Long presses retain the device's power behavior.
`screen.push.select {"index":0..4}` provides the same view selection remotely.
`screen.push.get` returns `view_index`, `queued`, `queue_capacity` (16),
`image_capacity` (4), `stack_capacity` (4), the full `queue` and 16 recent
`messages`. Notification states are
`queued/displayed/confirmed/timedout/dismissed/failed`.
Four transient SDRAM image slots, each at most 128 KiB, 1..480 × 1..854.
Unreferenced images expire after 120 seconds; MCU reboot clears them.
A decode failure marks that notification failed and advances the queue.

Resize/compress at the caller. Supports 8-bit baseline sequential JPEG,
three-component YCbCr, common 4:4:4/4:2:2/4:2:0 sampling and a single scan.
Progressive, grayscale, CMYK and restart intervals are rejected. WebUI converts
PNG/JPEG/WebP in the browser; the CLI uses Pillow:

```sh
python3 -m pip install msgpack Pillow
python3 BRY88BBA15G/tools/screen_media.py prepare --image photo.png --width 320 --height 240 --output push.jpg
python3 BRY88BBA15G/tools/screen_media.py --url http://device push --image photo.png --title 'Delivery arrived' --mode confirm
python3 BRY88BBA15G/tools/screen_media.py --url http://device get push
```

`IOTCLOUD_AUTH` supplies an existing `admin:password`. The CLI waits for every MCU
receipt. Camera passwords come from `G3_CAMERA_PASSWORD`, not command arguments.

## Camera pull

`screen.stream.set`: required `url` (at most 383 bytes), `username/password`
at most 63 bytes each; `width` default 320 (1..480), `height` default 240
(1..854), `fps` default 1 (1..10), `enabled` default true, `verify_tls` default
true. HTTP/HTTPS paths accept `{width}/{height}/{fps}`. Embedded credentials,
IPv6 literals, fragments and redirects are unsupported. Omit password to retain
it; an empty password clears it. ESP NVS persists configuration. Queries expose
`password_set`, never the password.

```python
{"action":"screen.stream.set", "request_id":"camera-1", "params":{
 "url":"http://camera/mjpeg?w={width}&h={height}&fps={fps}",
 "width":320,"height":240,"fps":1,"enabled":True,"verify_tls":True}}
```

The screen MCU builds HTTP requests, handles Basic / Digest MD5 (qop=auth or
legacy no-qop), multipart MJPEG, HTTP chunked and single JPEG responses, then
validates and hardware-decodes to RGB565. ESP32 only relays bounded DNS/TCP/TLS
bytes with credit. Actual source frames must fit requested dimensions; the
source service determines whether URL parameters resize frames. Excess frames
are discarded without a backlog. RTSP/H.264 sources require a camera server
that produces MJPEG at the desired resolution.

Configure the source under Screen → Services → Camera; choose “Add camera page”
and save the layout. This adds a full 4×6 grid page and preserves existing pages.
Alternatively add an image component with contain/cover fit. SCN3 remains 9520
bytes; component `type=8`, offsets 86/87 are `image_source=0` /
`image_fit=0 contain,1 cover`. Maximum eight pages, 32 components.

Pulling runs only while an image component is visible, the screen is awake and
neither push nor OTA obscures it. Hidden/sleeping closes the connection; failures
back off from 1 to 30 seconds. Parameterless `screen.stream.start/stop` persist
the enabled flag. `get` returns configuration, state
(off/paused/connecting/reading/backoff), frames, dropped, bytes, actual
resolution/rate, pixel CRC and error. TLS verification defaults on; explicitly
disable it for a test source with a self-signed certificate.

## UART rates and recovery

`screen.link.get` returns configured/actual rates, session, CRC/framing errors,
retries and fallbacks. `set` accepts `mode:"fixed"|"auto"`, `rate`, `max_rate`,
`apply_now`. Rates: 115200, 230400, 460800, 921600; default fixed 115200. Auto
tries downward from its ceiling. Switching occurs only during MCU recovery:
drain TX, READY at old rate, CRC probe at new rate, mutual confirmation;
timeout falls back to 115200. `apply_now:true` restarts the screen MCU to enter
recovery negotiation; otherwise settings apply at the next recovery. High rates
hold ESP APB/no-light-sleep locks. Normal operation never upgrades rates on its
own; a reboot of either endpoint resynchronizes.

Binary frames use zero delimiters and escaping `00 → DB DC`, `DB → DB DD`.
Unescaped content is `"GM",version=1,channel,u32LE session,u32LE sequence,`
`u16LE length,payload,CRC32LE`; CRC covers header and payload, maximum payload
640 bytes. Channels: link=0, command=1, reply=2, socket=3, socket_ack=4,
socket_event=5. Image/TCP chunks are at most 512 bytes with one outstanding
credit and bounded retries. Session isolates old boots; sequence/content checks
handle duplicates. Factory OTA has exclusive raw UART access.
Results: 0 success, 1 range, 2 busy, 3 not found, 4 CRC, 5 format, 6 decode,
7 offline. See the [machine-readable contract](contracts/daikin-g3-media-v1.json).

Media opcodes are begin=1, chunk=2, commit=3, cancel=4, push=5, dismiss=6,
query=7, stream_config=8, stream_start=9, stream_stop=10, select=11. Select has
one u8 index after its opcode. Media status version 2 is 324 bytes followed by
40 bytes of stream status: base header 32 bytes; four image records of 17 bytes;
sixteen queue records of 9 bytes (u32 id, u32 image_id, u8 state); sixteen history
records of 5 bytes (u32 id, u8 state). Header bytes 22/23 are selected view /
queue count, 24/25 are JPEG SR / IR flags shifted by 10, 26..27 decode time in
ms (u16LE), 28..31 are message/image/view capacities and status version. The
ESP also accepts the earlier 172-byte snapshot during rolling upgrades.
