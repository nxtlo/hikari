#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © Nekoka.tt 2019-2020
#
# This file is part of Hikari.
#
# Hikari is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari. If not, see <https://www.gnu.org/licenses/>.
"""Basic implementation of an entity factory for general bots and REST apps."""

from __future__ import annotations

__all__ = ["EntityFactoryImpl"]

import datetime
import typing

from hikari.api import app as app_
from hikari.api import entity_factory
from hikari.models import applications
from hikari.models import audit_logs
from hikari.models import channels as channels_
from hikari.models import colors
from hikari.models import embeds
from hikari.models import emojis
from hikari.models import gateway
from hikari.models import guilds
from hikari.models import invites
from hikari.models import messages
from hikari.models import permissions
from hikari.models import presences as presences_
from hikari.models import users
from hikari.models import voices
from hikari.models import webhooks
from hikari.utilities import date
from hikari.utilities import snowflake
from hikari.utilities import undefined

if typing.TYPE_CHECKING:
    from hikari.utilities import data_binding

DMChannelT = typing.TypeVar("DMChannelT", bound=channels_.DMChannel)
GuildChannelT = typing.TypeVar("GuildChannelT", bound=channels_.GuildChannel)
InviteT = typing.TypeVar("InviteT", bound=invites.Invite)
PartialChannelT = typing.TypeVar("PartialChannelT", bound=channels_.PartialChannel)
PartialGuildT = typing.TypeVar("PartialGuildT", bound=guilds.PartialGuild)
PartialGuildIntegrationT = typing.TypeVar("PartialGuildIntegrationT", bound=guilds.PartialIntegration)
UserT = typing.TypeVar("UserT", bound=users.User)


def _deserialize_seconds_timedelta(seconds: typing.Union[str, int]) -> datetime.timedelta:
    return datetime.timedelta(seconds=int(seconds))


def _deserialize_day_timedelta(days: typing.Union[str, int]) -> datetime.timedelta:
    return datetime.timedelta(days=int(days))


def _deserialize_max_uses(age: int) -> typing.Union[int, float]:
    return age if age > 0 else float("inf")


def _deserialize_max_age(seconds: int) -> typing.Optional[datetime.timedelta]:
    return datetime.timedelta(seconds=seconds) if seconds > 0 else None


class EntityFactoryImpl(entity_factory.IEntityFactory):
    """Standard implementation for a serializer/deserializer.

    This will convert objects to/from JSON compatible representations.
    """

    def __init__(self, app: app_.IApp) -> None:
        self._app = app
        self._audit_log_entry_converters = {
            audit_logs.AuditLogChangeKey.OWNER_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.AFK_CHANNEL_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.AFK_TIMEOUT: _deserialize_seconds_timedelta,
            audit_logs.AuditLogChangeKey.MFA_LEVEL: guilds.GuildMFALevel,
            audit_logs.AuditLogChangeKey.VERIFICATION_LEVEL: guilds.GuildVerificationLevel,
            audit_logs.AuditLogChangeKey.EXPLICIT_CONTENT_FILTER: guilds.GuildExplicitContentFilterLevel,
            audit_logs.AuditLogChangeKey.DEFAULT_MESSAGE_NOTIFICATIONS: guilds.GuildMessageNotificationsLevel,
            audit_logs.AuditLogChangeKey.PRUNE_DELETE_DAYS: _deserialize_day_timedelta,
            audit_logs.AuditLogChangeKey.WIDGET_CHANNEL_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.POSITION: int,
            audit_logs.AuditLogChangeKey.BITRATE: int,
            audit_logs.AuditLogChangeKey.APPLICATION_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.PERMISSIONS: permissions.Permission,
            audit_logs.AuditLogChangeKey.COLOR: colors.Color,
            audit_logs.AuditLogChangeKey.ALLOW: permissions.Permission,
            audit_logs.AuditLogChangeKey.DENY: permissions.Permission,
            audit_logs.AuditLogChangeKey.CHANNEL_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.INVITER_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.MAX_USES: _deserialize_max_uses,
            audit_logs.AuditLogChangeKey.USES: int,
            audit_logs.AuditLogChangeKey.MAX_AGE: _deserialize_max_age,
            audit_logs.AuditLogChangeKey.ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.TYPE: str,
            audit_logs.AuditLogChangeKey.ENABLE_EMOTICONS: bool,
            audit_logs.AuditLogChangeKey.EXPIRE_BEHAVIOR: guilds.IntegrationExpireBehaviour,
            audit_logs.AuditLogChangeKey.EXPIRE_GRACE_PERIOD: _deserialize_day_timedelta,
            audit_logs.AuditLogChangeKey.RATE_LIMIT_PER_USER: _deserialize_seconds_timedelta,
            audit_logs.AuditLogChangeKey.SYSTEM_CHANNEL_ID: snowflake.Snowflake,
            audit_logs.AuditLogChangeKey.ADD_ROLE_TO_MEMBER: self._deserialize_audit_log_change_roles,
            audit_logs.AuditLogChangeKey.REMOVE_ROLE_FROM_MEMBER: self._deserialize_audit_log_change_roles,
            audit_logs.AuditLogChangeKey.PERMISSION_OVERWRITES: self._deserialize_audit_log_overwrites,
        }
        self._audit_log_event_mapping = {
            audit_logs.AuditLogEventType.CHANNEL_OVERWRITE_CREATE: self._deserialize_channel_overwrite_entry_info,
            audit_logs.AuditLogEventType.CHANNEL_OVERWRITE_UPDATE: self._deserialize_channel_overwrite_entry_info,
            audit_logs.AuditLogEventType.CHANNEL_OVERWRITE_DELETE: self._deserialize_channel_overwrite_entry_info,
            audit_logs.AuditLogEventType.MESSAGE_PIN: self._deserialize_message_pin_entry_info,
            audit_logs.AuditLogEventType.MESSAGE_UNPIN: self._deserialize_message_pin_entry_info,
            audit_logs.AuditLogEventType.MEMBER_PRUNE: self._deserialize_member_prune_entry_info,
            audit_logs.AuditLogEventType.MESSAGE_BULK_DELETE: self._deserialize_message_bulk_delete_entry_info,
            audit_logs.AuditLogEventType.MESSAGE_DELETE: self._deserialize_message_delete_entry_info,
            audit_logs.AuditLogEventType.MEMBER_DISCONNECT: self._deserialize_member_disconnect_entry_info,
            audit_logs.AuditLogEventType.MEMBER_MOVE: self._deserialize_member_move_entry_info,
        }
        self._channel_type_mapping = {
            channels_.ChannelType.DM: self.deserialize_dm_channel,
            channels_.ChannelType.GROUP_DM: self.deserialize_group_dm_channel,
            channels_.ChannelType.GUILD_CATEGORY: self.deserialize_guild_category,
            channels_.ChannelType.GUILD_TEXT: self.deserialize_guild_text_channel,
            channels_.ChannelType.GUILD_NEWS: self.deserialize_guild_news_channel,
            channels_.ChannelType.GUILD_STORE: self.deserialize_guild_store_channel,
            channels_.ChannelType.GUILD_VOICE: self.deserialize_guild_voice_channel,
        }

    @property
    def app(self) -> app_.IApp:
        return self._app

    ################
    # APPLICATIONS #
    ################

    def deserialize_own_connection(self, payload: data_binding.JSONObject) -> applications.OwnConnection:
        own_connection = applications.OwnConnection()
        own_connection.id = snowflake.Snowflake(payload["id"])
        own_connection.name = payload["name"]
        own_connection.type = payload["type"]
        own_connection.is_revoked = payload.get("revoked")
        own_connection.integrations = [
            self.deserialize_partial_integration(integration) for integration in payload.get("integrations", ())
        ]
        own_connection.is_verified = payload["verified"]
        own_connection.is_friend_syncing = payload["friend_sync"]
        own_connection.is_showing_activity = payload["show_activity"]
        # noinspection PyArgumentList
        own_connection.visibility = applications.ConnectionVisibility(payload["visibility"])
        return own_connection

    def deserialize_own_guild(self, payload: data_binding.JSONObject) -> applications.OwnGuild:
        own_guild = self._set_partial_guild_attributes(payload, applications.OwnGuild())
        own_guild.is_owner = bool(payload["owner"])
        # noinspection PyArgumentList
        own_guild.my_permissions = permissions.Permission(payload["permissions"])
        return own_guild

    def deserialize_application(self, payload: data_binding.JSONObject) -> applications.Application:
        application = applications.Application()
        application.set_app(self._app)
        application.id = snowflake.Snowflake(payload["id"])
        application.name = payload["name"]
        application.description = payload["description"]
        application.is_bot_public = payload.get("bot_public")
        application.is_bot_code_grant_required = payload.get("bot_require_code_grant")
        application.owner = self.deserialize_user(payload["owner"]) if "owner" in payload else None
        application.rpc_origins = set(payload["rpc_origins"]) if "rpc_origins" in payload else None
        application.summary = payload["summary"]
        application.verify_key = bytes(payload["verify_key"], "utf-8") if "verify_key" in payload else None
        application.icon_hash = payload.get("icon")

        if (team_payload := payload.get("team")) is not None:
            team = applications.Team()
            team.set_app(self._app)
            team.id = snowflake.Snowflake(team_payload["id"])
            team.icon_hash = team_payload["icon"]

            members = {}
            for member_payload in team_payload["members"]:
                team_member = applications.TeamMember()
                team_member.set_app(self._app)
                # noinspection PyArgumentList
                team_member.membership_state = applications.TeamMembershipState(member_payload["membership_state"])
                team_member.permissions = set(member_payload["permissions"])
                team_member.team_id = snowflake.Snowflake(member_payload["team_id"])
                team_member.user = self.deserialize_user(member_payload["user"])
                members[team_member.user.id] = team_member
            team.members = members

            team.owner_user_id = snowflake.Snowflake(team_payload["owner_user_id"])
            application.team = team
        else:
            application.team = None

        application.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None
        application.primary_sku_id = (
            snowflake.Snowflake(payload["primary_sku_id"]) if "primary_sku_id" in payload else None
        )
        application.slug = payload.get("slug")
        application.cover_image_hash = payload.get("cover_image")
        return application

    ##############
    # AUDIT_LOGS #
    ##############

    def _deserialize_audit_log_change_roles(
        self, payload: data_binding.JSONArray
    ) -> typing.Mapping[snowflake.Snowflake, guilds.PartialRole]:
        roles = {}
        for role_payload in payload:
            role = guilds.PartialRole()
            role.set_app(self._app)
            role.id = snowflake.Snowflake(role_payload["id"])
            role.name = role_payload["name"]
            roles[role.id] = role
        return roles

    def _deserialize_audit_log_overwrites(
        self, payload: data_binding.JSONArray
    ) -> typing.Mapping[snowflake.Snowflake, channels_.PermissionOverwrite]:
        return {
            snowflake.Snowflake(overwrite["id"]): self.deserialize_permission_overwrite(overwrite)
            for overwrite in payload
        }

    @staticmethod
    def _deserialize_channel_overwrite_entry_info(
        payload: data_binding.JSONObject,
    ) -> audit_logs.ChannelOverwriteEntryInfo:
        channel_overwrite_entry_info = audit_logs.ChannelOverwriteEntryInfo()
        channel_overwrite_entry_info.id = snowflake.Snowflake(payload["id"])
        # noinspection PyArgumentList
        channel_overwrite_entry_info.type = channels_.PermissionOverwriteType(payload["type"])
        channel_overwrite_entry_info.role_name = payload.get("role_name")
        return channel_overwrite_entry_info

    @staticmethod
    def _deserialize_message_pin_entry_info(payload: data_binding.JSONObject) -> audit_logs.MessagePinEntryInfo:
        message_pin_entry_info = audit_logs.MessagePinEntryInfo()
        message_pin_entry_info.channel_id = snowflake.Snowflake(payload["channel_id"])
        message_pin_entry_info.message_id = snowflake.Snowflake(payload["message_id"])
        return message_pin_entry_info

    @staticmethod
    def _deserialize_member_prune_entry_info(payload: data_binding.JSONObject) -> audit_logs.MemberPruneEntryInfo:
        member_prune_entry_info = audit_logs.MemberPruneEntryInfo()
        member_prune_entry_info.delete_member_days = datetime.timedelta(days=int(payload["delete_member_days"]))
        member_prune_entry_info.members_removed = int(payload["members_removed"])
        return member_prune_entry_info

    @staticmethod
    def _deserialize_message_bulk_delete_entry_info(
        payload: data_binding.JSONObject,
    ) -> audit_logs.MessageBulkDeleteEntryInfo:
        message_bulk_delete_entry_info = audit_logs.MessageBulkDeleteEntryInfo()
        message_bulk_delete_entry_info.count = int(payload["count"])
        return message_bulk_delete_entry_info

    @staticmethod
    def _deserialize_message_delete_entry_info(payload: data_binding.JSONObject) -> audit_logs.MessageDeleteEntryInfo:
        message_delete_entry_info = audit_logs.MessageDeleteEntryInfo()
        message_delete_entry_info.channel_id = snowflake.Snowflake(payload["channel_id"])
        message_delete_entry_info.count = int(payload["count"])
        return message_delete_entry_info

    @staticmethod
    def _deserialize_member_disconnect_entry_info(
        payload: data_binding.JSONObject,
    ) -> audit_logs.MemberDisconnectEntryInfo:
        member_disconnect_entry_info = audit_logs.MemberDisconnectEntryInfo()
        member_disconnect_entry_info.count = int(payload["count"])
        return member_disconnect_entry_info

    @staticmethod
    def _deserialize_member_move_entry_info(payload: data_binding.JSONObject) -> audit_logs.MemberMoveEntryInfo:
        member_move_entry_info = audit_logs.MemberMoveEntryInfo()
        member_move_entry_info.channel_id = snowflake.Snowflake(payload["channel_id"])
        member_move_entry_info.count = int(payload["count"])
        return member_move_entry_info

    @staticmethod
    def _deserialize_unrecognised_audit_log_entry_info(
        payload: data_binding.JSONObject,
    ) -> audit_logs.UnrecognisedAuditLogEntryInfo:
        return audit_logs.UnrecognisedAuditLogEntryInfo(payload)

    def deserialize_audit_log(self, payload: data_binding.JSONObject) -> audit_logs.AuditLog:
        audit_log = audit_logs.AuditLog()

        entries = {}
        for entry_payload in payload["audit_log_entries"]:
            entry = audit_logs.AuditLogEntry()
            entry.set_app(self._app)
            entry.id = snowflake.Snowflake(entry_payload["id"])

            if (target_id := entry_payload["target_id"]) is not None:
                target_id = snowflake.Snowflake(target_id)
            entry.target_id = target_id

            changes = []
            for change_payload in entry_payload.get("changes", ()):
                change = audit_logs.AuditLogChange()

                try:
                    # noinspection PyArgumentList
                    change.key = audit_logs.AuditLogChangeKey(change_payload["key"])
                except ValueError:
                    change.key = change_payload["key"]

                new_value = change_payload.get("new_value")
                old_value = change_payload.get("old_value")
                if value_converter := self._audit_log_entry_converters.get(change.key):
                    new_value = value_converter(new_value) if new_value is not None else None
                    old_value = value_converter(old_value) if old_value is not None else None
                change.new_value = new_value
                change.old_value = old_value

                changes.append(change)
            entry.changes = changes

            if (user_id := entry_payload["user_id"]) is not None:
                user_id = snowflake.Snowflake(user_id)
            entry.user_id = user_id

            try:
                # noinspection PyArgumentList
                entry.action_type = audit_logs.AuditLogEventType(entry_payload["action_type"])
            except ValueError:
                entry.action_type = entry_payload["action_type"]

            if (options := entry_payload.get("options")) is not None:
                option_converter = (
                    self._audit_log_event_mapping.get(entry.action_type)
                    or self._deserialize_unrecognised_audit_log_entry_info
                )
                options = option_converter(options)
            entry.options = options

            entry.reason = entry_payload.get("reason")
            entries[entry.id] = entry
        audit_log.entries = entries

        audit_log.integrations = {
            snowflake.Snowflake(integration["id"]): self.deserialize_partial_integration(integration)
            for integration in payload["integrations"]
        }
        audit_log.users = {snowflake.Snowflake(user["id"]): self.deserialize_user(user) for user in payload["users"]}
        audit_log.webhooks = {
            snowflake.Snowflake(webhook["id"]): self.deserialize_webhook(webhook) for webhook in payload["webhooks"]
        }
        return audit_log

    ############
    # CHANNELS #
    ############

    def deserialize_permission_overwrite(self, payload: data_binding.JSONObject) -> channels_.PermissionOverwrite:
        # noinspection PyArgumentList
        permission_overwrite = channels_.PermissionOverwrite(
            id=snowflake.Snowflake(payload["id"]), type=channels_.PermissionOverwriteType(payload["type"]),
        )
        # noinspection PyArgumentList
        permission_overwrite.allow = permissions.Permission(payload["allow"])
        # noinspection PyArgumentList
        permission_overwrite.deny = permissions.Permission(payload["deny"])
        return permission_overwrite

    def serialize_permission_overwrite(self, overwrite: channels_.PermissionOverwrite) -> data_binding.JSONObject:
        return {"id": str(overwrite.id), "type": overwrite.type, "allow": overwrite.allow, "deny": overwrite.deny}

    def _set_partial_channel_attributes(
        self, payload: data_binding.JSONObject, channel: PartialChannelT
    ) -> PartialChannelT:
        channel.set_app(self._app)
        channel.id = snowflake.Snowflake(payload["id"])
        channel.name = payload.get("name")
        # noinspection PyArgumentList
        channel.type = channels_.ChannelType(payload["type"])
        return channel

    def deserialize_partial_channel(self, payload: data_binding.JSONObject) -> channels_.PartialChannel:
        return self._set_partial_channel_attributes(payload, channels_.PartialChannel())

    def _set_dm_channel_attributes(self, payload: data_binding.JSONObject, channel: DMChannelT) -> DMChannelT:
        channel = self._set_partial_channel_attributes(payload, channel)

        if (last_message_id := payload["last_message_id"]) is not None:
            last_message_id = snowflake.Snowflake(last_message_id)

        channel.last_message_id = last_message_id
        channel.recipients = {
            snowflake.Snowflake(user["id"]): self.deserialize_user(user) for user in payload["recipients"]
        }
        return channel

    def deserialize_dm_channel(self, payload: data_binding.JSONObject) -> channels_.DMChannel:
        return self._set_dm_channel_attributes(payload, channels_.DMChannel())

    def deserialize_group_dm_channel(self, payload: data_binding.JSONObject) -> channels_.GroupDMChannel:
        group_dm_channel = self._set_dm_channel_attributes(payload, channels_.GroupDMChannel())
        group_dm_channel.owner_id = snowflake.Snowflake(payload["owner_id"])
        group_dm_channel.icon_hash = payload["icon"]
        group_dm_channel.application_id = (
            snowflake.Snowflake(payload["application_id"]) if "application_id" in payload else None
        )
        return group_dm_channel

    def _set_guild_channel_attributes(self, payload: data_binding.JSONObject, channel: GuildChannelT) -> GuildChannelT:
        channel = self._set_partial_channel_attributes(payload, channel)
        channel.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None
        channel.position = int(payload["position"])
        channel.permission_overwrites = {
            snowflake.Snowflake(overwrite["id"]): self.deserialize_permission_overwrite(overwrite)
            for overwrite in payload["permission_overwrites"]
        }  # TODO: while snowflakes are guaranteed to be unique within their own resource, there is no guarantee for
        # across between resources (user and role in this case); while in practice we won't get overlap there is a
        # chance that this may happen in the future, would it be more sensible to use a Sequence here?
        channel.is_nsfw = payload.get("nsfw")

        if (parent_id := payload.get("parent_id")) is not None:
            parent_id = snowflake.Snowflake(parent_id)
        channel.parent_id = parent_id

        return channel

    def deserialize_guild_category(self, payload: data_binding.JSONObject) -> channels_.GuildCategory:
        return self._set_guild_channel_attributes(payload, channels_.GuildCategory())

    def deserialize_guild_text_channel(self, payload: data_binding.JSONObject) -> channels_.GuildTextChannel:
        guild_text_category = self._set_guild_channel_attributes(payload, channels_.GuildTextChannel())
        guild_text_category.topic = payload["topic"]

        if (last_message_id := payload["last_message_id"]) is not None:
            last_message_id = snowflake.Snowflake(last_message_id)
        guild_text_category.last_message_id = last_message_id

        guild_text_category.rate_limit_per_user = datetime.timedelta(seconds=payload["rate_limit_per_user"])

        if (last_pin_timestamp := payload.get("last_pin_timestamp")) is not None:
            last_pin_timestamp = date.iso8601_datetime_string_to_datetime(last_pin_timestamp)
        guild_text_category.last_pin_timestamp = last_pin_timestamp

        return guild_text_category

    def deserialize_guild_news_channel(self, payload: data_binding.JSONObject) -> channels_.GuildNewsChannel:
        guild_news_channel = self._set_guild_channel_attributes(payload, channels_.GuildNewsChannel())
        guild_news_channel.topic = payload["topic"]

        if (last_message_id := payload["last_message_id"]) is not None:
            last_message_id = snowflake.Snowflake(last_message_id)
        guild_news_channel.last_message_id = last_message_id

        if (last_pin_timestamp := payload.get("last_pin_timestamp")) is not None:
            last_pin_timestamp = date.iso8601_datetime_string_to_datetime(last_pin_timestamp)
        guild_news_channel.last_pin_timestamp = last_pin_timestamp

        return guild_news_channel

    def deserialize_guild_store_channel(self, payload: data_binding.JSONObject) -> channels_.GuildStoreChannel:
        return self._set_guild_channel_attributes(payload, channels_.GuildStoreChannel())

    def deserialize_guild_voice_channel(self, payload: data_binding.JSONObject) -> channels_.GuildVoiceChannel:
        guild_voice_channel = self._set_guild_channel_attributes(payload, channels_.GuildVoiceChannel())
        guild_voice_channel.bitrate = int(payload["bitrate"])
        guild_voice_channel.user_limit = int(payload["user_limit"])
        return guild_voice_channel

    def deserialize_channel(self, payload: data_binding.JSONObject) -> channels_.PartialChannel:
        # noinspection PyArgumentList
        return self._channel_type_mapping[payload["type"]](payload)

    ##########
    # EMBEDS #
    ##########

    def deserialize_embed(self, payload: data_binding.JSONObject) -> embeds.Embed:
        embed = embeds.Embed()
        embed.title = payload.get("title")
        embed.description = payload.get("description")
        embed.url = payload.get("url")
        embed.timestamp = (
            date.iso8601_datetime_string_to_datetime(payload["timestamp"]) if "timestamp" in payload else None
        )
        embed.color = colors.Color(payload["color"]) if "color" in payload else None

        if (footer_payload := payload.get("footer", ...)) is not ...:
            footer = embeds.EmbedFooter()
            footer.text = footer_payload["text"]
            footer.icon_url = footer_payload.get("icon_url")
            footer.proxy_icon_url = footer_payload.get("proxy_icon_url")
            embed.footer = footer
        else:
            embed.footer = None

        if (image_payload := payload.get("image", ...)) is not ...:
            image = embeds.EmbedImage()
            image.url = image_payload.get("url")
            image.proxy_url = image_payload.get("proxy_url")
            image.height = int(image_payload["height"]) if "height" in image_payload else None
            image.width = int(image_payload["width"]) if "width" in image_payload else None
            embed.image = image
        else:
            embed.image = None

        if (thumbnail_payload := payload.get("thumbnail", ...)) is not ...:
            thumbnail = embeds.EmbedThumbnail()
            thumbnail.url = thumbnail_payload.get("url")
            thumbnail.proxy_url = thumbnail_payload.get("proxy_url")
            thumbnail.height = int(thumbnail_payload["height"]) if "height" in thumbnail_payload else None
            thumbnail.width = int(thumbnail_payload["width"]) if "width" in thumbnail_payload else None
            embed.thumbnail = thumbnail
        else:
            embed.thumbnail = None

        if (video_payload := payload.get("video", ...)) is not ...:
            video = embeds.EmbedVideo()
            video.url = video_payload.get("url")
            video.height = int(video_payload["height"]) if "height" in video_payload else None
            video.width = int(video_payload["width"]) if "width" in video_payload else None
            embed.video = video
        else:
            embed.video = None

        if (provider_payload := payload.get("provider", ...)) is not ...:
            provider = embeds.EmbedProvider()
            provider.name = provider_payload.get("name")
            provider.url = provider_payload.get("url")
            embed.provider = provider
        else:
            embed.provider = None

        if (author_payload := payload.get("author", ...)) is not ...:
            author = embeds.EmbedAuthor()
            author.name = author_payload.get("name")
            author.url = author_payload.get("url")
            author.icon_url = author_payload.get("icon_url")
            author.proxy_icon_url = author_payload.get("proxy_icon_url")
            embed.author = author
        else:
            embed.author = None

        fields = []
        for field_payload in payload.get("fields", ()):
            field = embeds.EmbedField()
            field.name = field_payload["name"]
            field.value = field_payload["value"]
            field.is_inline = field_payload.get("inline", False)
            fields.append(field)
        embed.fields = fields

        return embed

    def serialize_embed(self, embed: embeds.Embed) -> data_binding.JSONObject:
        payload = {}

        if embed.title is not None:
            payload["title"] = embed.title

        if embed.description is not None:
            payload["description"] = embed.description

        if embed.url is not None:
            payload["url"] = embed.url

        if embed.timestamp is not None:
            payload["timestamp"] = embed.timestamp.isoformat()

        if embed.color is not None:
            payload["color"] = embed.color

        if embed.footer is not None:
            footer_payload = {}

            if embed.footer.text is not None:
                footer_payload["text"] = embed.footer.text

            if embed.footer.icon_url is not None:
                footer_payload["icon_url"] = embed.footer.icon_url

            payload["footer"] = footer_payload

        if embed.image is not None:
            image_payload = {}

            if embed.image.url is not None:
                image_payload["url"] = embed.image.url

            payload["image"] = image_payload

        if embed.thumbnail is not None:
            thumbnail_payload = {}

            if embed.thumbnail.url is not None:
                thumbnail_payload["url"] = embed.thumbnail.url

            payload["thumbnail"] = thumbnail_payload

        if embed.author is not None:
            author_payload = {}

            if embed.author.name is not None:
                author_payload["name"] = embed.author.name

            if embed.author.url is not None:
                author_payload["url"] = embed.author.url

            if embed.author.icon_url is not None:
                author_payload["icon_url"] = embed.author.icon_url

            payload["author"] = author_payload

        if embed.fields:
            field_payloads = []
            for field in embed.fields:
                field_payload = {}

                if field.name:
                    field_payload["name"] = field.name

                if field.value:
                    field_payload["value"] = field.value

                field_payload["inline"] = field.is_inline
                field_payloads.append(field_payload)
            payload["fields"] = field_payloads

        return payload

    ##########
    # EMOJIS #
    ##########

    def deserialize_unicode_emoji(self, payload: data_binding.JSONObject) -> emojis.UnicodeEmoji:
        unicode_emoji = emojis.UnicodeEmoji()
        unicode_emoji.name = payload["name"]
        return unicode_emoji

    def deserialize_custom_emoji(self, payload: data_binding.JSONObject) -> emojis.CustomEmoji:
        custom_emoji = emojis.CustomEmoji()
        custom_emoji.set_app(self._app)
        custom_emoji.id = snowflake.Snowflake(payload["id"])
        custom_emoji.name = payload["name"]
        custom_emoji.is_animated = payload.get("animated", False)
        return custom_emoji

    def deserialize_known_custom_emoji(self, payload: data_binding.JSONObject) -> emojis.KnownCustomEmoji:
        known_custom_emoji = emojis.KnownCustomEmoji()
        known_custom_emoji.set_app(self._app)
        known_custom_emoji.id = snowflake.Snowflake(payload["id"])
        known_custom_emoji.name = payload["name"]
        known_custom_emoji.is_animated = payload.get("animated", False)
        known_custom_emoji.role_ids = {snowflake.Snowflake(role_id) for role_id in payload.get("roles", ())}

        if (user := payload.get("user")) is not None:
            user = self.deserialize_user(user)
        known_custom_emoji.user = user

        known_custom_emoji.is_colons_required = payload["require_colons"]
        known_custom_emoji.is_managed = payload["managed"]
        known_custom_emoji.is_available = payload["available"]
        return known_custom_emoji

    def deserialize_emoji(
        self, payload: data_binding.JSONObject
    ) -> typing.Union[emojis.UnicodeEmoji, emojis.CustomEmoji]:
        if payload.get("id") is not None:
            return self.deserialize_custom_emoji(payload)

        return self.deserialize_unicode_emoji(payload)

    ###########
    # GATEWAY #
    ###########

    def deserialize_gateway_bot(self, payload: data_binding.JSONObject) -> gateway.GatewayBot:
        gateway_bot = gateway.GatewayBot()
        gateway_bot.url = payload["url"]
        gateway_bot.shard_count = int(payload["shards"])
        session_start_limit_payload = payload["session_start_limit"]
        session_start_limit = gateway.SessionStartLimit()
        session_start_limit.total = int(session_start_limit_payload["total"])
        session_start_limit.remaining = int(session_start_limit_payload["remaining"])
        session_start_limit.reset_after = datetime.timedelta(milliseconds=session_start_limit_payload["reset_after"])
        # I do not trust that this may never be zero for some unknown reason. If it was 0, it
        # would hang the application on start up, so I enforce it is at least 1.
        session_start_limit.max_concurrency = max(session_start_limit_payload.get("max_concurrency", 0), 1)
        gateway_bot.session_start_limit = session_start_limit
        return gateway_bot

    ##########
    # GUILDS #
    ##########

    def deserialize_guild_widget(self, payload: data_binding.JSONObject) -> guilds.GuildWidget:
        guild_embed = guilds.GuildWidget()
        guild_embed.set_app(self._app)

        if (channel_id := payload["channel_id"]) is not None:
            channel_id = snowflake.Snowflake(channel_id)
        guild_embed.channel_id = channel_id

        guild_embed.is_enabled = payload["enabled"]
        return guild_embed

    def deserialize_member(
        self,
        payload: data_binding.JSONObject,
        *,
        user: typing.Union[undefined.Undefined, users.User] = undefined.Undefined()
    ) -> guilds.Member:
        guild_member = guilds.Member()
        guild_member.set_app(self._app)
        guild_member.user = user or self.deserialize_user(payload["user"])
        guild_member.nickname = payload.get("nick")
        guild_member.role_ids = {snowflake.Snowflake(role_id) for role_id in payload["roles"]}
        guild_member.joined_at = date.iso8601_datetime_string_to_datetime(payload["joined_at"])

        if (premium_since := payload.get("premium_since")) is not None:
            premium_since = date.iso8601_datetime_string_to_datetime(premium_since)
        guild_member.premium_since = premium_since

        guild_member.is_deaf = payload["deaf"]
        guild_member.is_mute = payload["mute"]
        return guild_member

    def deserialize_role(self, payload: data_binding.JSONObject) -> guilds.Role:
        guild_role = guilds.Role()
        guild_role.set_app(self._app)
        guild_role.id = snowflake.Snowflake(payload["id"])
        guild_role.name = payload["name"]
        guild_role.color = colors.Color(payload["color"])
        guild_role.is_hoisted = payload["hoist"]
        guild_role.position = int(payload["position"])
        # noinspection PyArgumentList
        guild_role.permissions = permissions.Permission(payload["permissions"])
        guild_role.is_managed = payload["managed"]
        guild_role.is_mentionable = payload["mentionable"]
        return guild_role

    @staticmethod
    def _set_partial_integration_attributes(
        payload: data_binding.JSONObject, integration: PartialGuildIntegrationT
    ) -> PartialGuildIntegrationT:
        integration.id = snowflake.Snowflake(payload["id"])
        integration.name = payload["name"]
        integration.type = payload["type"]
        account_payload = payload["account"]
        account = guilds.IntegrationAccount()
        account.id = account_payload["id"]
        account.name = account_payload["name"]
        integration.account = account
        return integration

    def deserialize_partial_integration(self, payload: data_binding.JSONObject) -> guilds.PartialIntegration:
        return self._set_partial_integration_attributes(payload, guilds.PartialIntegration())

    def deserialize_integration(self, payload: data_binding.JSONObject) -> guilds.Integration:
        guild_integration = self._set_partial_integration_attributes(payload, guilds.Integration())
        guild_integration.is_enabled = payload["enabled"]
        guild_integration.is_syncing = payload["syncing"]

        if (role_id := payload.get("role_id")) is not None:
            role_id = snowflake.Snowflake(role_id)
        guild_integration.role_id = role_id

        guild_integration.is_emojis_enabled = payload.get("enable_emoticons")
        # noinspection PyArgumentList
        guild_integration.expire_behavior = guilds.IntegrationExpireBehaviour(payload["expire_behavior"])
        guild_integration.expire_grace_period = datetime.timedelta(days=payload["expire_grace_period"])
        guild_integration.user = self.deserialize_user(payload["user"])

        if (last_synced_at := payload["synced_at"]) is not None:
            last_synced_at = date.iso8601_datetime_string_to_datetime(last_synced_at)
        guild_integration.last_synced_at = last_synced_at

        return guild_integration

    def deserialize_guild_member_ban(self, payload: data_binding.JSONObject) -> guilds.GuildMemberBan:
        guild_member_ban = guilds.GuildMemberBan()
        guild_member_ban.reason = payload["reason"]
        guild_member_ban.user = self.deserialize_user(payload["user"])
        return guild_member_ban

    def deserialize_unavailable_guild(self, payload: data_binding.JSONObject) -> guilds.UnavailableGuild:
        unavailable_guild = guilds.UnavailableGuild()
        unavailable_guild.set_app(self._app)
        unavailable_guild.id = snowflake.Snowflake(payload["id"])
        return unavailable_guild

    def _set_partial_guild_attributes(self, payload: data_binding.JSONObject, guild: PartialGuildT) -> PartialGuildT:
        guild.set_app(self._app)
        guild.id = snowflake.Snowflake(payload["id"])
        guild.name = payload["name"]
        guild.icon_hash = payload["icon"]

        features = []
        for feature in payload["features"]:
            try:
                # noinspection PyArgumentList
                features.append(guilds.GuildFeature(feature))
            except ValueError:
                features.append(feature)
        guild.features = set(features)

        return guild

    def deserialize_guild_preview(self, payload: data_binding.JSONObject) -> guilds.GuildPreview:
        guild_preview = self._set_partial_guild_attributes(payload, guilds.GuildPreview())
        guild_preview.splash_hash = payload["splash"]
        guild_preview.discovery_splash_hash = payload["discovery_splash"]
        guild_preview.emojis = {
            snowflake.Snowflake(emoji["id"]): self.deserialize_known_custom_emoji(emoji) for emoji in payload["emojis"]
        }
        guild_preview.approximate_presence_count = int(payload["approximate_presence_count"])
        guild_preview.approximate_member_count = int(payload["approximate_member_count"])
        guild_preview.description = payload["description"]
        return guild_preview

    def deserialize_guild(self, payload: data_binding.JSONObject) -> guilds.Guild:
        guild = self._set_partial_guild_attributes(payload, guilds.Guild())
        guild.splash_hash = payload["splash"]
        guild.discovery_splash_hash = payload["discovery_splash"]
        guild.owner_id = snowflake.Snowflake(payload["owner_id"])
        # noinspection PyArgumentList
        guild.my_permissions = permissions.Permission(payload["permissions"]) if "permissions" in payload else None
        guild.region = payload["region"]

        if (afk_channel_id := payload["afk_channel_id"]) is not None:
            afk_channel_id = snowflake.Snowflake(afk_channel_id)
        guild.afk_channel_id = afk_channel_id

        guild.afk_timeout = datetime.timedelta(seconds=payload["afk_timeout"])
        guild.is_embed_enabled = payload.get("embed_enabled", False)

        if (embed_channel_id := payload.get("embed_channel_id")) is not None:
            embed_channel_id = snowflake.Snowflake(embed_channel_id)
        guild.embed_channel_id = embed_channel_id

        # noinspection PyArgumentList
        guild.verification_level = guilds.GuildVerificationLevel(payload["verification_level"])
        # noinspection PyArgumentList
        guild.default_message_notifications = guilds.GuildMessageNotificationsLevel(
            payload["default_message_notifications"]
        )
        # noinspection PyArgumentList
        guild.explicit_content_filter = guilds.GuildExplicitContentFilterLevel(payload["explicit_content_filter"])
        guild.roles = {snowflake.Snowflake(role["id"]): self.deserialize_role(role) for role in payload["roles"]}
        guild.emojis = {
            snowflake.Snowflake(emoji["id"]): self.deserialize_known_custom_emoji(emoji) for emoji in payload["emojis"]
        }
        # noinspection PyArgumentList
        guild.mfa_level = guilds.GuildMFALevel(payload["mfa_level"])

        if (application_id := payload["application_id"]) is not None:
            application_id = snowflake.Snowflake(application_id)
        guild.application_id = application_id

        guild.is_unavailable = payload["unavailable"] if "unavailable" in payload else None
        guild.is_widget_enabled = payload["widget_enabled"] if "widget_enabled" in payload else None

        if (widget_channel_id := payload.get("widget_channel_id")) is not None:
            widget_channel_id = snowflake.Snowflake(widget_channel_id)
        guild.widget_channel_id = widget_channel_id

        if (system_channel_id := payload["system_channel_id"]) is not None:
            system_channel_id = snowflake.Snowflake(system_channel_id)
        guild.system_channel_id = system_channel_id

        # noinspection PyArgumentList
        guild.system_channel_flags = guilds.GuildSystemChannelFlag(payload["system_channel_flags"])

        if (rules_channel_id := payload["rules_channel_id"]) is not None:
            rules_channel_id = snowflake.Snowflake(rules_channel_id)
        guild.rules_channel_id = rules_channel_id

        guild.joined_at = (
            date.iso8601_datetime_string_to_datetime(payload["joined_at"]) if "joined_at" in payload else None
        )
        guild.is_large = payload["large"] if "large" in payload else None
        guild.member_count = int(payload["member_count"]) if "member_count" in payload else None

        if (members := payload.get("members", ...)) is not ...:
            guild.members = {
                snowflake.Snowflake(member["user"]["id"]): self.deserialize_member(member) for member in members
            }
        else:
            guild.members = None

        if (channels := payload.get("channels", ...)) is not ...:
            guild.channels = {
                snowflake.Snowflake(channel["id"]): self.deserialize_channel(channel) for channel in channels
            }
        else:
            guild.channels = None

        if (presences := payload.get("presences", ...)) is not ...:
            guild.presences = {
                snowflake.Snowflake(presence["user"]["id"]): self.deserialize_member_presence(presence)
                for presence in presences
            }
        else:
            guild.presences = None

        if (max_presences := payload.get("max_presences")) is not None:
            max_presences = int(max_presences)
        guild.max_presences = max_presences

        guild.max_members = int(payload["max_members"]) if "max_members" in payload else None
        guild.max_video_channel_users = (
            int(payload["max_video_channel_users"]) if "max_video_channel_users" in payload else None
        )
        guild.vanity_url_code = payload["vanity_url_code"]
        guild.description = payload["description"]
        guild.banner_hash = payload["banner"]
        # noinspection PyArgumentList
        guild.premium_tier = guilds.GuildPremiumTier(payload["premium_tier"])

        if (premium_subscription_count := payload.get("premium_subscription_count")) is not None:
            premium_subscription_count = int(premium_subscription_count)
        guild.premium_subscription_count = premium_subscription_count

        guild.preferred_locale = payload["preferred_locale"]

        if (public_updates_channel_id := payload["public_updates_channel_id"]) is not None:
            public_updates_channel_id = snowflake.Snowflake(public_updates_channel_id)
        guild.public_updates_channel_id = public_updates_channel_id

        guild.approximate_member_count = (
            int(payload["approximate_member_count"]) if "approximate_member_count" in payload else None
        )
        guild.approximate_active_member_count = (
            int(payload["approximate_presence_count"]) if "approximate_presence_count" in payload else None
        )
        return guild

    ###########
    # INVITES #
    ###########

    def deserialize_vanity_url(self, payload: data_binding.JSONObject) -> invites.VanityURL:
        vanity_url = invites.VanityURL()
        vanity_url.set_app(self._app)
        vanity_url.code = payload["code"]
        vanity_url.uses = int(payload["uses"])
        return vanity_url

    def _set_invite_attributes(self, payload: data_binding.JSONObject, invite: InviteT) -> InviteT:
        invite.set_app(self._app)
        invite.code = payload["code"]

        if (guild_payload := payload.get("guild", ...)) is not ...:
            guild = self._set_partial_guild_attributes(guild_payload, invites.InviteGuild())
            guild.splash_hash = guild_payload["splash"]
            guild.banner_hash = guild_payload["banner"]
            guild.description = guild_payload["description"]
            # noinspection PyArgumentList
            guild.verification_level = guilds.GuildVerificationLevel(guild_payload["verification_level"])
            guild.vanity_url_code = guild_payload["vanity_url_code"]
            invite.guild = guild
        else:
            invite.guild = None

        invite.channel = self.deserialize_partial_channel(payload["channel"])
        invite.inviter = self.deserialize_user(payload["inviter"]) if "inviter" in payload else None
        invite.target_user = self.deserialize_user(payload["target_user"]) if "target_user" in payload else None
        # noinspection PyArgumentList
        invite.target_user_type = (
            invites.TargetUserType(payload["target_user_type"]) if "target_user_type" in payload else None
        )
        invite.approximate_presence_count = (
            int(payload["approximate_presence_count"]) if "approximate_presence_count" in payload else None
        )
        invite.approximate_member_count = (
            int(payload["approximate_member_count"]) if "approximate_member_count" in payload else None
        )
        return invite

    def deserialize_invite(self, payload: data_binding.JSONObject) -> invites.Invite:
        return self._set_invite_attributes(payload, invites.Invite())

    def deserialize_invite_with_metadata(self, payload: data_binding.JSONObject) -> invites.InviteWithMetadata:
        invite_with_metadata = self._set_invite_attributes(payload, invites.InviteWithMetadata())
        invite_with_metadata.uses = int(payload["uses"])
        invite_with_metadata.max_uses = int(payload["max_uses"])
        max_age = payload["max_age"]
        invite_with_metadata.max_age = datetime.timedelta(seconds=max_age) if max_age > 0 else None
        invite_with_metadata.is_temporary = payload["temporary"]
        invite_with_metadata.created_at = date.iso8601_datetime_string_to_datetime(payload["created_at"])
        return invite_with_metadata

    ############
    # MESSAGES #
    ############

    # TODO: arbitrarily partial ver?
    def deserialize_message(self, payload: data_binding.JSONObject) -> messages.Message:
        message = messages.Message()
        message.set_app(self._app)
        message.id = snowflake.Snowflake(payload["id"])
        message.channel_id = snowflake.Snowflake(payload["channel_id"])
        message.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None
        message.author = self.deserialize_user(payload["author"])
        message.member = (
            self.deserialize_member(payload["member"], user=message.author) if "member" in payload else None
        )
        message.content = payload["content"]
        message.timestamp = date.iso8601_datetime_string_to_datetime(payload["timestamp"])

        if (edited_timestamp := payload["edited_timestamp"]) is not None:
            edited_timestamp = date.iso8601_datetime_string_to_datetime(edited_timestamp)
        message.edited_timestamp = edited_timestamp

        message.is_tts = payload["tts"]
        message.is_mentioning_everyone = payload["mention_everyone"]
        message.user_mentions = {snowflake.Snowflake(mention["id"]) for mention in payload["mentions"]}
        message.role_mentions = {snowflake.Snowflake(mention) for mention in payload["mention_roles"]}
        message.channel_mentions = {
            snowflake.Snowflake(mention["id"]) for mention in payload.get("mention_channels", ())
        }

        attachments = []
        for attachment_payload in payload["attachments"]:
            attachment = messages.Attachment()
            attachment.id = snowflake.Snowflake(attachment_payload["id"])
            attachment.filename = attachment_payload["filename"]
            attachment.size = int(attachment_payload["size"])
            attachment.url = attachment_payload["url"]
            attachment.proxy_url = attachment_payload["proxy_url"]
            attachment.height = attachment_payload.get("height")
            attachment.width = attachment_payload.get("width")
            attachments.append(attachment)
        message.attachments = attachments

        message.embeds = [self.deserialize_embed(embed) for embed in payload["embeds"]]

        reactions = []
        for reaction_payload in payload.get("reactions", ()):
            reaction = messages.Reaction()
            reaction.count = int(reaction_payload["count"])
            reaction.emoji = self.deserialize_emoji(reaction_payload["emoji"])
            reaction.is_reacted_by_me = reaction_payload["me"]
            reactions.append(reaction)
        message.reactions = reactions

        message.is_pinned = payload["pinned"]
        message.webhook_id = snowflake.Snowflake(payload["webhook_id"]) if "webhook_id" in payload else None
        # noinspection PyArgumentList
        message.type = messages.MessageType(payload["type"])

        if (activity_payload := payload.get("activity", ...)) is not ...:
            activity = messages.MessageActivity()
            # noinspection PyArgumentList
            activity.type = messages.MessageActivityType(activity_payload["type"])
            activity.party_id = activity_payload.get("party_id")
            message.activity = activity
        else:
            message.activity = None

        message.application = self.deserialize_application(payload["application"]) if "application" in payload else None

        if (crosspost_payload := payload.get("message_reference", ...)) is not ...:
            crosspost = messages.MessageCrosspost()
            crosspost.set_app(self._app)
            crosspost.id = (
                snowflake.Snowflake(crosspost_payload["message_id"]) if "message_id" in crosspost_payload else None
            )
            crosspost.channel_id = snowflake.Snowflake(crosspost_payload["channel_id"])
            crosspost.guild_id = (
                snowflake.Snowflake(crosspost_payload["guild_id"]) if "guild_id" in crosspost_payload else None
            )
            message.message_reference = crosspost
        else:
            message.message_reference = None

        # noinspection PyArgumentList
        message.flags = messages.MessageFlag(payload["flags"]) if "flags" in payload else None
        message.nonce = payload.get("nonce")
        return message

    #############
    # PRESENCES #
    #############

    def deserialize_member_presence(self, payload: data_binding.JSONObject) -> presences_.MemberPresence:
        guild_member_presence = presences_.MemberPresence()
        guild_member_presence.set_app(self._app)
        user_payload = payload["user"]
        user = presences_.PresenceUser()
        user.set_app(self._app)
        user.id = snowflake.Snowflake(user_payload["id"])
        user.discriminator = user_payload["discriminator"] if "discriminator" in user_payload else undefined.Undefined()
        user.username = user_payload["username"] if "username" in user_payload else undefined.Undefined()
        user.avatar_hash = user_payload["avatar"] if "avatar" in user_payload else undefined.Undefined()
        user.is_bot = user_payload["bot"] if "bot" in user_payload else undefined.Undefined()
        user.is_system = user_payload["system"] if "system" in user_payload else undefined.Undefined()
        # noinspection PyArgumentList
        user.flags = (
            users.UserFlag(user_payload["public_flags"]) if "public_flags" in user_payload else undefined.Undefined()
        )
        guild_member_presence.user = user

        if (role_ids := payload.get("roles", ...)) is not ...:
            guild_member_presence.role_ids = {snowflake.Snowflake(role_id) for role_id in role_ids}
        else:
            guild_member_presence.role_ids = None

        guild_member_presence.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None
        # noinspection PyArgumentList
        guild_member_presence.visible_status = presences_.PresenceStatus(payload["status"])

        activities = []
        for activity_payload in payload["activities"]:
            activity = presences_.RichActivity()
            activity.name = activity_payload["name"]
            # noinspection PyArgumentList
            activity.type = presences_.ActivityType(activity_payload["type"])
            activity.url = activity_payload.get("url")
            activity.created_at = date.unix_epoch_to_datetime(activity_payload["created_at"])

            if (timestamps_payload := activity_payload.get("timestamps", ...)) is not ...:
                timestamps = presences_.ActivityTimestamps()
                timestamps.start = (
                    date.unix_epoch_to_datetime(timestamps_payload["start"]) if "start" in timestamps_payload else None
                )
                timestamps.end = (
                    date.unix_epoch_to_datetime(timestamps_payload["end"]) if "end" in timestamps_payload else None
                )
                activity.timestamps = timestamps
            else:
                activity.timestamps = None

            activity.application_id = (
                snowflake.Snowflake(activity_payload["application_id"])
                if "application_id" in activity_payload
                else None
            )
            activity.details = activity_payload.get("details")
            activity.state = activity_payload.get("state")

            if (emoji := activity_payload.get("emoji")) is not None:
                emoji = self.deserialize_emoji(emoji)
            activity.emoji = emoji

            if (party_payload := activity_payload.get("party", ...)) is not ...:
                party = presences_.ActivityParty()
                party.id = party_payload.get("id")

                if (size := party_payload.get("size", ...)) is not ...:
                    party.current_size = int(size[0])
                    party.max_size = int(size[1])
                else:
                    party.current_size = party.max_size = None

                activity.party = party
            else:
                activity.party = None

            if (assets_payload := activity_payload.get("assets", ...)) is not ...:
                assets = presences_.ActivityAssets()
                assets.large_image = assets_payload.get("large_image")
                assets.large_text = assets_payload.get("large_text")
                assets.small_image = assets_payload.get("small_image")
                assets.small_text = assets_payload.get("small_text")
                activity.assets = assets
            else:
                activity.assets = None

            if (secrets_payload := activity_payload.get("secrets", ...)) is not ...:
                secret = presences_.ActivitySecret()
                secret.join = secrets_payload.get("join")
                secret.spectate = secrets_payload.get("spectate")
                secret.match = secrets_payload.get("match")
                activity.secrets = secret
            else:
                activity.secrets = None

            activity.is_instance = activity_payload.get("instance")  # TODO: can we safely default this to False?
            # noinspection PyArgumentList
            activity.flags = presences_.ActivityFlag(activity_payload["flags"]) if "flags" in activity_payload else None
            activities.append(activity)
        guild_member_presence.activities = activities

        client_status_payload = payload["client_status"]
        client_status = presences_.ClientStatus()
        # noinspection PyArgumentList
        client_status.desktop = (
            presences_.PresenceStatus(client_status_payload["desktop"])
            if "desktop" in client_status_payload
            else presences_.PresenceStatus.OFFLINE
        )
        # noinspection PyArgumentList
        client_status.mobile = (
            presences_.PresenceStatus(client_status_payload["mobile"])
            if "mobile" in client_status_payload
            else presences_.PresenceStatus.OFFLINE
        )
        # noinspection PyArgumentList
        client_status.web = (
            presences_.PresenceStatus(client_status_payload["web"])
            if "web" in client_status_payload
            else presences_.PresenceStatus.OFFLINE
        )
        guild_member_presence.client_status = client_status

        # TODO: do we want to differentiate between undefined and null here?
        if (premium_since := payload.get("premium_since")) is not None:
            premium_since = date.iso8601_datetime_string_to_datetime(premium_since)
        guild_member_presence.premium_since = premium_since

        # TODO: do we want to differentiate between undefined and null here?
        guild_member_presence.nickname = payload.get("nick")
        return guild_member_presence

    #########
    # USERS #
    #########

    def _set_user_attributes(self, payload: data_binding.JSONObject, user: UserT) -> UserT:
        user.set_app(self._app)
        user.id = snowflake.Snowflake(payload["id"])
        user.discriminator = payload["discriminator"]
        user.username = payload["username"]
        user.avatar_hash = payload["avatar"]
        user.is_bot = payload.get("bot", False)
        user.is_system = payload.get("system", False)
        return user

    def deserialize_user(self, payload: data_binding.JSONObject) -> users.User:
        user = self._set_user_attributes(payload, users.User())
        # noinspection PyArgumentList
        user.flags = users.UserFlag(payload["public_flags"]) if "public_flags" in payload else users.UserFlag.NONE
        return user

    def deserialize_my_user(self, payload: data_binding.JSONObject) -> users.OwnUser:
        my_user = self._set_user_attributes(payload, users.OwnUser())
        my_user.is_mfa_enabled = payload["mfa_enabled"]
        my_user.locale = payload.get("locale")
        my_user.is_verified = payload.get("verified")
        my_user.email = payload.get("email")
        # noinspection PyArgumentList
        my_user.flags = users.UserFlag(payload["flags"])
        # noinspection PyArgumentList
        my_user.premium_type = users.PremiumType(payload["premium_type"]) if "premium_type" in payload else None
        return my_user

    ##########
    # Voices #
    ##########

    def deserialize_voice_state(self, payload: data_binding.JSONObject) -> voices.VoiceState:
        voice_state = voices.VoiceState()
        voice_state.set_app(self._app)
        voice_state.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None

        if (channel_id := payload["channel_id"]) is not None:
            channel_id = snowflake.Snowflake(channel_id)
        voice_state.channel_id = channel_id

        voice_state.user_id = snowflake.Snowflake(payload["user_id"])
        voice_state.member = self.deserialize_member(payload["member"]) if "member" in payload else None
        voice_state.session_id = payload["session_id"]
        voice_state.is_guild_deafened = payload["deaf"]
        voice_state.is_guild_muted = payload["mute"]
        voice_state.is_self_deafened = payload["self_deaf"]
        voice_state.is_self_muted = payload["self_mute"]
        voice_state.is_streaming = payload.get("self_stream", False)
        voice_state.is_suppressed = payload["suppress"]
        return voice_state

    def deserialize_voice_region(self, payload: data_binding.JSONObject) -> voices.VoiceRegion:
        voice_region = voices.VoiceRegion()
        voice_region.id = payload["id"]
        voice_region.name = payload["name"]
        voice_region.is_vip = payload["vip"]
        voice_region.is_optimal_location = payload["optimal"]
        voice_region.is_deprecated = payload["deprecated"]
        voice_region.is_custom = payload["custom"]
        return voice_region

    ############
    # WEBHOOKS #
    ############

    def deserialize_webhook(self, payload: data_binding.JSONObject) -> webhooks.Webhook:
        webhook = webhooks.Webhook()
        webhook.id = snowflake.Snowflake(payload["id"])
        # noinspection PyArgumentList
        webhook.type = webhooks.WebhookType(payload["type"])
        webhook.guild_id = snowflake.Snowflake(payload["guild_id"]) if "guild_id" in payload else None
        webhook.channel_id = snowflake.Snowflake(payload["channel_id"])
        webhook.author = self.deserialize_user(payload["user"]) if "user" in payload else None
        webhook.name = payload["name"]
        webhook.avatar_hash = payload["avatar"]
        webhook.token = payload.get("token")
        return webhook
