"""今日老婆插件主体。"""
from __future__ import annotations

import os
import time
import random
from typing import Optional

from maibot_sdk import MaiBotPlugin, Command, CONFIG_RELOAD_SCOPE_SELF

from .config import WifePickerConfig
from .utils import PersistStore, fetch_avatar_base64, today_str


class WifePickerPlugin(MaiBotPlugin):
    config_model = WifePickerConfig

    # ---------------- 生命周期 ----------------

    async def on_load(self) -> None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        self._store = PersistStore(os.path.join(data_dir, "wife_picker_seen.json"))
        self._last_action: dict = {}
        self._bot_qq_cache: Optional[str] = None
        self.ctx.logger.info("✅ wife_picker 已加载")

    async def on_unload(self) -> None:
        store = getattr(self, "_store", None)
        if store is not None:
            await store.save()

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info(f"wife_picker 配置已更新: {version}")
            # 配置 bot_qq 改了，清缓存让下次重新解析
            self._bot_qq_cache = None

    # ---------------- 上下文解析 ----------------

    def _extract_ctx(self, kwargs: dict):
        """从命令回调 kwargs 中提取 group_id / sender_qq / sender_name。"""
        base_info = kwargs.get("message_base_info", {}) or {}
        user_info = base_info.get("user_info", {}) or {}
        group_info = base_info.get("group_info", {}) or {}

        group_id = kwargs.get("group_id") or group_info.get("group_id")
        sender_qq = kwargs.get("user_id") or user_info.get("user_id")

        # raw_event 兜底（部分适配器经此路径透传）
        if not group_id and "raw_event" in kwargs:
            raw_event = kwargs["raw_event"]
            if isinstance(raw_event, dict):
                group_id = raw_event.get("group_id")
            else:
                group_id = getattr(raw_event, "group_id", None)
        if not sender_qq and "raw_event" in kwargs:
            raw_event = kwargs["raw_event"]
            if isinstance(raw_event, dict):
                sender_qq = raw_event.get("user_id")

        sender_name = (
            user_info.get("user_cardname")
            or user_info.get("user_nickname")
            or ""
        )
        return (
            str(group_id) if group_id else None,
            str(sender_qq) if sender_qq else None,
            sender_name,
        )

    async def _resolve_bot_qq(self) -> Optional[str]:
        if self._bot_qq_cache:
            return self._bot_qq_cache
        cfg_qq = (self.config.wife_picker.bot_qq or "").strip()
        if cfg_qq:
            self._bot_qq_cache = cfg_qq
            return cfg_qq
        try:
            info = await self.ctx.api.call("adapter.napcat.system.get_login_info")
            if isinstance(info, dict):
                uid = info.get("user_id") or (info.get("data") or {}).get("user_id")
                if uid:
                    self._bot_qq_cache = str(uid)
                    return self._bot_qq_cache
        except Exception as e:
            self.ctx.logger.warning(f"无法自动获取机器人 QQ: {e}")
        return None

    # 通过 napcat 适配器 API 直接发送图片

    async def _send_napcat(self, group_id: int, message_chain: list) -> None:
        try:
            await self.ctx.api.call(
                "adapter.napcat.message.send_msg",
                params={
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": message_chain,
                },
            )
        except Exception as e:
            self.ctx.logger.error(f"napcat 发送失败: {e}")

    async def _send_text_at(self, group_id: str, sender_qq: str, text: str) -> None:
        chain = []
        if sender_qq and sender_qq.isdigit():
            chain.append({"type": "at", "data": {"qq": str(sender_qq)}})
            chain.append({"type": "text", "data": {"text": " "}})
        chain.append({"type": "text", "data": {"text": text}})
        await self._send_napcat(int(group_id), chain)

    async def _send_wife_message(
        self,
        group_id: str,
        sender_qq: str,
        wife_uid: str,
        wife_nick: str,
        wife_card: str,
        prefix: str,
    ) -> None:
        nick = wife_nick or "未知昵称"
        lines = [f"\n💕 {prefix}：", f"🌸 QQ名：{nick}"]
        if wife_card and wife_card != wife_nick:
            lines.append(f"🏷️ 群昵称：{wife_card}")
        lines.append(f"🆔 QQ号：{wife_uid}")
        text = "\n".join(lines)

        chain: list = []
        if sender_qq and sender_qq.isdigit():
            chain.append({"type": "at", "data": {"qq": str(sender_qq)}})
        chain.append({"type": "text", "data": {"text": text}})

        if self.config.wife_picker.send_avatar:
            size = int(self.config.wife_picker.avatar_size or 640)
            b64 = await fetch_avatar_base64(wife_uid, size=size)
            if b64:
                chain.append({"type": "text", "data": {"text": "\n"}})
                chain.append({"type": "image", "data": {"file": f"base64://{b64}"}})

        await self._send_napcat(int(group_id), chain)

    # ---------------- 冷却 ----------------

    def _check_cooldown(self, group_id: str, sender_qq: str, command: str) -> bool:
        """True = 命中冷却，应当拦截。"""
        key = f"{group_id}_{sender_qq}"
        now = time.time()
        last = self._last_action.get(key, {})
        cooldown = max(0, int(self.config.wife_picker.cooldown_seconds or 60))
        if last.get("command") == command and now - last.get("time", 0.0) < cooldown:
            return True
        self._last_action[key] = {"command": command, "time": now}
        return False

    # ---------------- /今日老婆 ----------------

    @Command(
        "wife_picker",
        description="随机抽取今日老婆",
        pattern=r"^/今日老婆$",
    )
    async def handle_wife_picker(self, stream_id: str = "", **kwargs):
        if not self.config.plugin.enabled:
            return False, None, False

        group_id, sender_qq, _ = self._extract_ctx(kwargs)
        if not group_id or not sender_qq:
            return True, "好像是私聊呢，去群聊里找你的老婆吧。", True

        if self._check_cooldown(group_id, sender_qq, "wife_picker"):
            self.ctx.logger.info(
                f"用户 {sender_qq} 在群 {group_id} 触发 /今日老婆 冷却，静默忽略。"
            )
            return True, "cooldown", True

        cfg = self.config.wife_picker
        today = today_str(cfg.tz_offset_hours)

        if self._store.purge_old(today) and cfg.persist_enabled:
            await self._store.save()

        no_limit_users = [str(x) for x in (cfg.no_limit_users or [])]
        daily = self._store.data.setdefault("daily", {})

        # 今日已抽：复读
        if sender_qq not in no_limit_users:
            rec = daily.get(group_id, {}).get(sender_qq)
            if isinstance(rec, dict) and rec.get("date") == today:
                await self._send_wife_message(
                    group_id, sender_qq,
                    str(rec.get("wife_uid", "未知")),
                    str(rec.get("wife_nick", "")),
                    str(rec.get("wife_card", "")),
                    prefix="你今天已经有老婆了哦，她是",
                )
                return True, "already_picked", True

        # 拉群成员
        try:
            members = await self.ctx.api.call(
                "adapter.napcat.group.get_group_member_list",
                group_id=int(group_id),
                no_cache=True,
            )
        except Exception as e:
            self.ctx.logger.error(f"获取群成员失败: {e}")
            await self._send_text_at(group_id, sender_qq, f"无法获取群成员列表：{e}")
            return False, "api_error", True

        if not isinstance(members, list) or not members:
            await self._send_text_at(group_id, sender_qq, "群成员列表数据异常。")
            return False, "api_error", True

        bot_qq = await self._resolve_bot_qq() if cfg.exclude_self else None

        # 筛选候选
        candidates = []
        for m in members:
            uid = str(m.get("user_id", ""))
            if not uid:
                continue
            if cfg.exclude_sender and uid == sender_qq:
                continue
            if bot_qq and uid == str(bot_qq):
                continue
            candidates.append(m)

        if not candidates:
            await self._send_text_at(
                group_id, sender_qq, "群里好像没人了（或者只有你和机器人）..."
            )
            return True, "no_candidates", True

        chosen = random.choice(candidates)
        wife_uid = str(chosen.get("user_id"))
        wife_card = str(chosen.get("card") or "")
        wife_nick = str(chosen.get("nickname") or "")

        await self._send_wife_message(
            group_id, sender_qq, wife_uid, wife_nick, wife_card,
            prefix="今天你的老婆是",
        )

        daily.setdefault(group_id, {})[sender_qq] = {
            "date": today,
            "wife_uid": wife_uid,
            "wife_nick": wife_nick,
            "wife_card": wife_card,
        }
        if cfg.persist_enabled:
            await self._store.save()

        return True, f"wife picked: {wife_card or wife_nick}", True

    # ---------------- /离婚 ----------------

    @Command(
        "wife_picker_divorce",
        description="清空今日老婆记录，可重新抽取（每日限一次）",
        pattern=r"^/离婚$",
    )
    async def handle_divorce(self, stream_id: str = "", **kwargs):
        if not self.config.plugin.enabled:
            return False, None, False

        group_id, sender_qq, _ = self._extract_ctx(kwargs)
        if not group_id or not sender_qq:
            return True, "只能在群里离婚喔～", True

        if self._check_cooldown(group_id, sender_qq, "divorce"):
            self.ctx.logger.info(
                f"用户 {sender_qq} 在群 {group_id} 触发 /离婚 冷却，静默忽略。"
            )
            return True, "cooldown", True

        cfg = self.config.wife_picker
        today = today_str(cfg.tz_offset_hours)

        if self._store.purge_old(today) and cfg.persist_enabled:
            await self._store.save()

        no_limit_users = [str(x) for x in (cfg.no_limit_users or [])]
        daily = self._store.data.setdefault("daily", {})
        divorce_usage = self._store.data.setdefault("divorce_usage", {})

        # 每日限一次
        if sender_qq not in no_limit_users:
            if divorce_usage.get(group_id, {}).get(sender_qq) == today:
                await self._send_text_at(
                    group_id, sender_qq, "感情不是儿戏，明天再来吧。（每日仅限一次离婚）"
                )
                return True, "limit_reached", True

        grp = daily.get(group_id, {})
        if sender_qq in grp:
            grp.pop(sender_qq, None)
            divorce_usage.setdefault(group_id, {})[sender_qq] = today
            if cfg.persist_enabled:
                await self._store.save()
            await self._send_text_at(
                group_id, sender_qq, "已经离婚成功，现在可以重新抽你的新老婆啦～"
            )
            return True, "divorced", True
        else:
            await self._send_text_at(
                group_id, sender_qq, "你今天还没有老婆呢，不需要离婚～"
            )
            return True, "no_record", True


def create_plugin():
    return WifePickerPlugin()