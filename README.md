# 今日老婆 (wife_picker)

> 适配MaiSaka的群聊娱乐插件 —— 每天在群里随机抽一个"老婆"，附带头像，支持离婚重抽。

---

## ✨ 特性

- 🎲 **每日随机抽取**：在群聊中输入 `/今日老婆`，从群成员中随机抽一位
- 🖼️ **附带头像**：自动下载并发送对方的 QQ 头像
- 💔 **支持离婚**：通过 `/离婚` 清空记录可重新抽取，每日限一次
- 🕐 **每日记录**：同一天内重复触发会返回当天已抽到的对象，不会重复抽取
- ⚙️ **可配置候选池**：可选择是否排除机器人自身、指令发起者
- 👑 **白名单机制**：白名单用户不受每日一次限制
- 🌍 **时区可调**：自定义"今日"的边界
- ⏱️ **连续触发冷却**：避免刷屏
- 💾 **本地持久化**：抽取记录与离婚记录跨重启保留

---

## 📦 安装

1. 将本插件目录放入 MaiBot 的 `plugins/` 下：

```
plugins/
└── wife_picker/
    ├── __init__.py
    ├── _manifest.json
    ├── config.toml
    ├── plugin.py
    ├── config.py
    └── utils.py
```

2. 启动（或重启）MaiBot，插件会被自动加载。

3. 首次启动后会在插件目录下自动创建 `data/wife_picker_seen.json` 用于持久化。

---

## 🎮 指令

| 指令 | 说明 |
|------|------|
| `/今日老婆` | 在群里随机抽取一位"今日老婆"；同一天再次触发会复述当天结果 |
| `/离婚` | 清空当天抽取记录，可重新抽取（每日限一次） |

> 仅支持在群聊中使用，私聊会被静默拒绝。

---

## ⚙️ 配置

配置文件：`plugins/wife_picker/config.toml`

```toml
[plugin]
enabled = true
config_version = "1.0.0"

[wife_picker]
# 是否将机器人自身排除出候选池
exclude_self = true

# 是否将指令发起者排除出候选池
exclude_sender = true

# （可选）机器人 QQ。留空时会自动通过 napcat 获取登录信息
bot_qq = ""

# 不受每日一次限制的白名单 QQ 列表
no_limit_users = []

# 时区偏移（小时），用于确定 "今日" 的边界。默认 +8（北京时间）
tz_offset_hours = 8

# 是否额外发送对方的 QQ 头像
send_avatar = true

# 头像尺寸（像素）
avatar_size = 640

# 同一指令连续触发的冷却秒数
cooldown_seconds = 60

# 是否启用本地持久化（保存今日抽取与离婚记录）
persist_enabled = true
```

### 字段说明

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `plugin.enabled` | bool | `true` | 插件总开关 |
| `wife_picker.exclude_self` | bool | `true` | 抽取时排除机器人 |
| `wife_picker.exclude_sender` | bool | `true` | 抽取时排除指令发起者 |
| `wife_picker.bot_qq` | str | `""` | 机器人 QQ；留空自动通过 napcat 获取并缓存 |
| `wife_picker.no_limit_users` | list | `[]` | 白名单 QQ（这些用户不受每日一次限制） |
| `wife_picker.tz_offset_hours` | int | `8` | 时区偏移小时，范围 `-12 ~ +14` |
| `wife_picker.send_avatar` | bool | `true` | 是否发送头像 |
| `wife_picker.avatar_size` | int | `640` | 头像尺寸 |
| `wife_picker.cooldown_seconds` | int | `60` | 连续相同指令的静默冷却时间 |
| `wife_picker.persist_enabled` | bool | `true` | 是否启用本地持久化 |

---

## 📁 数据持久化

数据文件：`plugins/wife_picker/data/wife_picker_seen.json`

结构示例：

```json
{
  "daily": {
    "123456": {
      "111111": {
        "date": "1919-08-10",
        "wife_uid": "114514",
        "wife_nick": "田所浩二",
        "wife_card": ""
      }
    }
  },
  "divorce_usage": {
    "123456": {
      "111111": "1919-08-10"
    }
  }
}
```

- `daily`：每个群每个用户当天抽到的对象
- `divorce_usage`：每个群每个用户最近一次离婚的日期

每天首次触发任意指令时，会自动清理非今日的过期记录。

---

## 📜 License

MIT
