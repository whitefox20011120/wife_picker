"""今日老婆插件配置模型。"""
from __future__ import annotations
from typing import ClassVar, List

from maibot_sdk import Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    __ui_label__: ClassVar[str] = "插件开关"
    __ui_order__: ClassVar[int] = 0

    enabled: bool = Field(
        default=True,
        description="是否启用本插件。",
        json_schema_extra={"label": "启用插件", "order": 0},
    )
    config_version: str = Field(
        default="1.0.0",
        json_schema_extra={"disabled": True, "hidden": True, "label": "配置版本", "order": 99},
    )


class WifePickerSection(PluginConfigBase):
    __ui_label__: ClassVar[str] = "今日老婆设置"
    __ui_order__: ClassVar[int] = 1

    exclude_self: bool = Field(
        default=True,
        description="是否将机器人自身排除出候选池。",
        json_schema_extra={"label": "排除机器人自身", "order": 0},
    )
    exclude_sender: bool = Field(
        default=True,
        description="是否将指令发起者排除出候选池。",
        json_schema_extra={"label": "排除指令发起者", "order": 1},
    )
    bot_qq: str = Field(
        default="",
        description="（可选）机器人 QQ。留空时自动通过 napcat 获取。",
        json_schema_extra={"label": "机器人 QQ（可选）", "placeholder": "留空自动获取", "order": 2},
    )
    no_limit_users: List[str] = Field(
        default_factory=list,
        description="不受每日一次限制的白名单 QQ 列表。",
        json_schema_extra={"label": "白名单 QQ", "order": 3},
    )
    tz_offset_hours: int = Field(
        default=8,
        description="时区偏移（小时），用于确定 “今日” 的边界。",
        json_schema_extra={"label": "时区偏移", "order": 4, "step": 1},
    )
    send_avatar: bool = Field(
        default=True,
        description="是否额外发送对方的 QQ 头像。",
        json_schema_extra={"label": "发送头像", "order": 5},
    )
    avatar_size: int = Field(
        default=640,
        description="头像尺寸（像素）。",
        json_schema_extra={"label": "头像尺寸", "order": 6, "step": 1},
    )
    cooldown_seconds: int = Field(
        default=60,
        description="同一指令连续触发的冷却秒数。",
        json_schema_extra={"label": "冷却秒数", "order": 7, "step": 1},
    )
    persist_enabled: bool = Field(
        default=True,
        description="是否启用本地持久化（保存今日抽取与离婚记录）。",
        json_schema_extra={"label": "启用持久化", "order": 8},
    )


class WifePickerConfig(PluginConfigBase):
    plugin: PluginSection = Field(default_factory=PluginSection)
    wife_picker: WifePickerSection = Field(default_factory=WifePickerSection)