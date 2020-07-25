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
import datetime

import mock
import pytest

from hikari import errors
from hikari.api.rest import app as rest_app
from hikari.impl import stateful_cache
from hikari.models import channels
from hikari.models import guilds
from hikari.models import users
from hikari.utilities import snowflake
from tests.hikari import hikari_test_helpers


class TestStatefulCacheComponentImpl:
    @pytest.fixture()
    def app_impl(self):
        return mock.Mock(rest_app.IApp)

    @pytest.fixture()
    def cache_impl(self, app_impl) -> stateful_cache.StatefulCacheComponentImpl:
        return hikari_test_helpers.unslot_class(stateful_cache.StatefulCacheComponentImpl)(app=app_impl, intents=None)

    def test_clear_dm_channels(self, cache_impl):
        dm_data_1 = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(5642134),
            name=None,
            last_message_id=snowflake.Snowflake(65345),
            recipient_id=snowflake.Snowflake(2342344),
        )
        dm_data_2 = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(867456345),
            name="NAME",
            last_message_id=snowflake.Snowflake(76765456),
            recipient_id=snowflake.Snowflake(978655),
        )
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._dm_channel_entries = {
            snowflake.Snowflake(978655): dm_data_1,
            snowflake.Snowflake(2342344): dm_data_2,
        }
        cache_impl._user_entries = {
            snowflake.Snowflake(2342344): mock_user_1,
            snowflake.Snowflake(653451234): mock.MagicMock(users.User),
            snowflake.Snowflake(978655): mock_user_2,
        }
        dm_mapping = cache_impl.clear_dm_channels()
        assert cache_impl._dm_channel_entries == {}
        assert 978655 in dm_mapping
        channel_from_view = dm_mapping[snowflake.Snowflake(978655)]
        assert channel_from_view.app is cache_impl.app
        assert channel_from_view.id == snowflake.Snowflake(5642134)
        assert channel_from_view.name is None
        assert channel_from_view.type is channels.ChannelType.DM
        assert channel_from_view.last_message_id == snowflake.Snowflake(65345)
        assert channel_from_view.recipient == mock_user_1
        assert 2342344 in dm_mapping
        channel_from_view = dm_mapping[snowflake.Snowflake(2342344)]
        assert channel_from_view.app is cache_impl.app
        assert channel_from_view.id == snowflake.Snowflake(867456345)
        assert channel_from_view.name == "NAME"
        assert channel_from_view.type is channels.ChannelType.DM
        assert channel_from_view.last_message_id == snowflake.Snowflake(76765456)
        assert channel_from_view.recipient == mock_user_2
        assert len(dm_mapping) == 2

    def test_clear_dm_channels_when_no_dm_channels_cached(self, cache_impl):
        assert cache_impl.clear_dm_channels() == {}

    def test_delete_dm_channel_for_known_dm_channel(self, cache_impl):
        dm_data = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(54234),
            name=None,
            last_message_id=snowflake.Snowflake(65345),
            recipient_id=snowflake.Snowflake(7345234),
        )
        mock_user = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        mock_dm_data = mock.MagicMock(stateful_cache._DMChannelData)
        cache_impl._dm_channel_entries = {
            snowflake.Snowflake(7345234): dm_data,
            snowflake.Snowflake(531234): mock_dm_data,
        }
        cache_impl._user_entries = {snowflake.Snowflake(7345234): mock_user, snowflake.Snowflake(7534521): mock_user_2}
        dm_channel = cache_impl.delete_dm_channel(snowflake.Snowflake(7345234))
        assert cache_impl._dm_channel_entries == {snowflake.Snowflake(531234): mock_dm_data}
        assert dm_channel.app is cache_impl.app
        assert dm_channel.id == snowflake.Snowflake(54234)
        assert dm_channel.name is None
        assert dm_channel.type is channels.ChannelType.DM
        assert dm_channel.last_message_id == snowflake.Snowflake(65345)
        assert dm_channel.recipient == mock_user

    def test_delete_dm_channel_for_unknown_dm_channel(self, cache_impl):
        assert cache_impl.delete_dm_channel(snowflake.Snowflake(564234123)) is None

    def test_get_dm_channel_for_known_dm_channel(self, cache_impl):
        dm_data = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(786456234),
            name="Namama",
            last_message_id=snowflake.Snowflake(653451234),
            recipient_id=snowflake.Snowflake(65234123),
        )
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(65234123): mock_user_1,
            snowflake.Snowflake(675234): mock_user_2,
        }
        cache_impl._dm_channel_entries = {
            snowflake.Snowflake(65234123): dm_data,
            snowflake.Snowflake(5123): mock.MagicMock(stateful_cache._DMChannelData),
        }
        dm_channel = cache_impl.get_dm_channel(snowflake.Snowflake(65234123))
        assert dm_channel.app is cache_impl.app
        assert dm_channel.id == snowflake.Snowflake(786456234)
        assert dm_channel.name == "Namama"
        assert dm_channel.type is channels.ChannelType.DM
        assert dm_channel.last_message_id == snowflake.Snowflake(653451234)
        assert dm_channel.recipient == mock_user_1

    def test_get_dm_channel_for_unknown_dm_channel(self, cache_impl):
        assert cache_impl.get_dm_channel(snowflake.Snowflake(561243)) is None

    def test_get_dm_channel_view(self, cache_impl):
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(54213): mock_user_1,
            snowflake.Snowflake(6764556): mock.MagicMock(users.User),
            snowflake.Snowflake(65656): mock_user_2,
        }
        dm_data_1 = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(875345),
            name=None,
            last_message_id=snowflake.Snowflake(3213),
            recipient_id=snowflake.Snowflake(54213),
        )
        dm_data_2 = stateful_cache._DMChannelData(
            id=snowflake.Snowflake(542134),
            name="OKOKOKOKOK",
            last_message_id=snowflake.Snowflake(85463),
            recipient_id=snowflake.Snowflake(65656),
        )
        cache_impl._dm_channel_entries = {snowflake.Snowflake(54213): dm_data_1, snowflake.Snowflake(65656): dm_data_2}
        dm_mapping = cache_impl.get_dm_channels_view()
        assert 54213 in dm_mapping
        current_dm = dm_mapping[snowflake.Snowflake(54213)]
        assert current_dm.app is cache_impl.app
        assert current_dm.id == snowflake.Snowflake(875345)
        assert current_dm.name is None
        assert current_dm.type is channels.ChannelType.DM
        assert current_dm.last_message_id == snowflake.Snowflake(3213)
        assert current_dm.recipient == mock_user_1
        assert 65656 in dm_mapping
        current_dm = dm_mapping[snowflake.Snowflake(65656)]
        assert current_dm.app is cache_impl.app
        assert current_dm.id == snowflake.Snowflake(542134)
        assert current_dm.name == "OKOKOKOKOK"
        assert current_dm.type is channels.ChannelType.DM
        assert current_dm.last_message_id == snowflake.Snowflake(85463)
        assert current_dm.recipient == mock_user_2
        assert len(dm_mapping) == 2

    def test_get_dm_channel_view_when_no_dm_channels_cached(self, cache_impl):
        assert cache_impl.get_dm_channels_view() == {}

    def test_set_dm_channel(self, cache_impl):
        mock_recipient = mock.MagicMock(users.User, id=snowflake.Snowflake(7652341234))
        dm_channel = channels.DMChannel()
        dm_channel.id = snowflake.Snowflake(23123)
        dm_channel.app = cache_impl.app
        dm_channel.name = None
        dm_channel.type = channels.ChannelType.DM
        dm_channel.recipient = mock_recipient
        dm_channel.last_message_id = snowflake.Snowflake(5432134234)
        cache_impl.set_dm_channel(dm_channel)
        assert 7652341234 in cache_impl._dm_channel_entries
        channel_data = cache_impl._dm_channel_entries[snowflake.Snowflake(7652341234)]
        assert channel_data.id == 23123
        assert not hasattr(channel_data, "app")
        assert channel_data.name is None
        assert not hasattr(channel_data, "type")
        assert not hasattr(channel_data, "recipient")
        assert channel_data.recipient_id == 7652341234
        assert channel_data.last_message_id == 5432134234

    def test_update_dm_channel(self, cache_impl):
        mock_old_cached_dm = mock.MagicMock(channels.DMChannel)
        mock_new_cached_dm = mock.MagicMock(channels.DMChannel)
        mock_dm_channel = mock.MagicMock(
            channels.DMChannel, recipient=mock.MagicMock(users.User, id=snowflake.Snowflake(53123123))
        )
        cache_impl.get_dm_channel = mock.MagicMock(side_effect=[mock_old_cached_dm, mock_new_cached_dm])
        cache_impl.set_dm_channel = mock.MagicMock()
        assert cache_impl.update_dm_channel(mock_dm_channel) == (mock_old_cached_dm, mock_new_cached_dm)
        cache_impl.set_dm_channel.assert_called_once_with(mock_dm_channel)
        cache_impl.get_dm_channel.assert_has_calls([mock.call(53123123), mock.call(53123123)])

    def test_clear_guilds_when_no_guilds_cached(self, cache_impl):
        cache_impl._guild_entries = {
            snowflake.Snowflake(423123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(675345): stateful_cache._GuildRecord(),
        }
        assert cache_impl.clear_guilds() == {}
        assert cache_impl._guild_entries == {
            snowflake.Snowflake(423123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(675345): stateful_cache._GuildRecord(),
        }

    def test_clear_guilds(self, cache_impl):
        mock_guild_1 = mock.MagicMock(guilds.GatewayGuild)
        mock_guild_2 = mock.MagicMock(guilds.GatewayGuild)
        mock_member = mock.MagicMock(guilds.Member)
        mock_guild_3 = mock.MagicMock(guilds.GatewayGuild)
        cache_impl._guild_entries = {
            snowflake.Snowflake(423123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(675345): stateful_cache._GuildRecord(guild=mock_guild_1),
            snowflake.Snowflake(32142): stateful_cache._GuildRecord(
                guild=mock_guild_2, members={snowflake.Snowflake(3241123): mock_member}
            ),
            snowflake.Snowflake(765345): stateful_cache._GuildRecord(guild=mock_guild_3),
            snowflake.Snowflake(321132): stateful_cache._GuildRecord(),
        }
        assert cache_impl.clear_guilds() == {675345: mock_guild_1, 32142: mock_guild_2, 765345: mock_guild_3}
        assert cache_impl._guild_entries == {
            snowflake.Snowflake(423123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(32142): stateful_cache._GuildRecord(
                members={snowflake.Snowflake(3241123): mock_member}
            ),
            snowflake.Snowflake(321132): stateful_cache._GuildRecord(),
        }

    def test_delete_guild_for_known_guild(self, cache_impl):
        mock_guild = mock.MagicMock(guilds.GatewayGuild)
        mock_member = mock.MagicMock(guilds.Member)
        cache_impl._guild_entries = {
            snowflake.Snowflake(354123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(
                guild=mock_guild, is_available=True, members={snowflake.Snowflake(43123): mock_member}
            ),
        }
        assert cache_impl.delete_guild(snowflake.Snowflake(543123)) is mock_guild
        assert cache_impl._guild_entries == {
            snowflake.Snowflake(354123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(members={snowflake.Snowflake(43123): mock_member}),
        }

    def test_delete_guild_for_removes_emptied_record(self, cache_impl):
        mock_guild = mock.MagicMock(guilds.GatewayGuild)
        cache_impl._guild_entries = {
            snowflake.Snowflake(354123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(guild=mock_guild, is_available=True),
        }
        assert cache_impl.delete_guild(snowflake.Snowflake(543123)) is mock_guild
        assert cache_impl._guild_entries == {snowflake.Snowflake(354123): stateful_cache._GuildRecord()}

    def test_delete_guild_for_unknown_guild(self, cache_impl):
        cache_impl._guild_entries = {
            snowflake.Snowflake(354123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(),
        }
        assert cache_impl.delete_guild(snowflake.Snowflake(543123)) is None
        assert cache_impl._guild_entries == {
            snowflake.Snowflake(354123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(),
        }

    def test_delete_guild_for_unknown_record(self, cache_impl):
        cache_impl._guild_entries = {snowflake.Snowflake(354123): stateful_cache._GuildRecord()}
        assert cache_impl.delete_guild(snowflake.Snowflake(543123)) is None
        assert cache_impl._guild_entries == {snowflake.Snowflake(354123): stateful_cache._GuildRecord()}

    def test_get_guild_for_known_guild_when_available(self, cache_impl):
        mock_guild = mock.MagicMock(guilds.GatewayGuild)
        cache_impl._guild_entries = {
            snowflake.Snowflake(54234123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(guild=mock_guild, is_available=True),
        }
        assert cache_impl.get_guild(snowflake.Snowflake(543123)) is mock_guild

    def test_get_guild_for_known_guild_when_unavailable(self, cache_impl):
        mock_guild = mock.MagicMock(guilds.GatewayGuild)
        cache_impl._guild_entries = {
            snowflake.Snowflake(54234123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(guild=mock_guild, is_available=False),
        }
        try:
            cache_impl.get_guild(snowflake.Snowflake(543123))
            assert False, "Excepted unavailable guild error to be raised"
        except errors.UnavailableGuildError:
            pass
        except Exception as exc:
            assert False, f"Expected unavailable guild error but got {exc}"

    def test_get_guild_for_unknown_guild(self, cache_impl):
        cache_impl._guild_entries = {
            snowflake.Snowflake(54234123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(543123): stateful_cache._GuildRecord(),
        }
        assert cache_impl.get_guild(snowflake.Snowflake(543123)) is None

    def test_get_guild_for_unknown_guild_record(self, cache_impl):
        cache_impl._guild_entries = {
            snowflake.Snowflake(54234123): stateful_cache._GuildRecord(),
        }
        assert cache_impl.get_guild(snowflake.Snowflake(543123)) is None

    def test_get_guilds_view(self, cache_impl):
        mock_guild_1 = mock.MagicMock(guilds.GatewayGuild)
        mock_guild_2 = mock.MagicMock(guilds.GatewayGuild)
        cache_impl._guild_entries = {
            snowflake.Snowflake(4312312): stateful_cache._GuildRecord(guild=mock_guild_1),
            snowflake.Snowflake(34123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(73453): stateful_cache._GuildRecord(guild=mock_guild_2),
        }
        assert cache_impl.get_guilds_view() == {
            snowflake.Snowflake(4312312): mock_guild_1,
            snowflake.Snowflake(73453): mock_guild_2,
        }

    def test_get_guilds_view_when_no_guilds_cached(self, cache_impl):
        cache_impl._guild_entries = {
            snowflake.Snowflake(4312312): stateful_cache._GuildRecord(),
            snowflake.Snowflake(34123): stateful_cache._GuildRecord(),
            snowflake.Snowflake(73453): stateful_cache._GuildRecord(),
        }
        assert cache_impl.get_guilds_view() == {}

    def test_set_guild(self, cache_impl):
        mock_guild = mock.MagicMock(guilds.GatewayGuild, id=snowflake.Snowflake(5123123))
        assert cache_impl.set_guild(mock_guild) is None
        assert 5123123 in cache_impl._guild_entries
        assert cache_impl._guild_entries[snowflake.Snowflake(5123123)].guild == mock_guild
        assert cache_impl._guild_entries[snowflake.Snowflake(5123123)].is_available is True

    def test_set_guild_availability(self, cache_impl):
        assert cache_impl.set_guild_availability(snowflake.Snowflake(43123), True) is None
        assert 43123 in cache_impl._guild_entries
        assert cache_impl._guild_entries[snowflake.Snowflake(43123)].is_available is True

    def test_set_initial_unavailable_guilds(self, cache_impl):
        result = cache_impl.set_initial_unavailable_guilds(
            [snowflake.Snowflake(1234), snowflake.Snowflake(6123123), snowflake.Snowflake(6654234)]
        )
        assert result is None
        assert 1234 in cache_impl._guild_entries
        assert cache_impl._guild_entries[snowflake.Snowflake(1234)].is_available is False
        assert 1234 in cache_impl._guild_entries
        assert cache_impl._guild_entries[snowflake.Snowflake(6123123)].is_available is False
        assert 1234 in cache_impl._guild_entries
        assert cache_impl._guild_entries[snowflake.Snowflake(6654234)].is_available is False

    def test_update_guild(self, cache_impl):
        ...

    def test_delete_me_for_known_me(self, cache_impl):
        mock_own_user = mock.MagicMock(users.OwnUser)
        cache_impl._me = mock_own_user
        assert cache_impl.delete_me() is mock_own_user
        assert cache_impl._me is None

    def test_delete_me_for_unknown_me(self, cache_impl):
        assert cache_impl.delete_me() is None
        assert cache_impl._me is None

    def test_get_me_for_known_me(self, cache_impl):
        mock_own_user = mock.MagicMock(users.OwnUser)
        cache_impl._me = mock_own_user
        assert cache_impl.get_me() == mock_own_user

    def test_get_me_for_unknown_me(self, cache_impl):
        assert cache_impl.get_me() is None

    def test_set_me(self, cache_impl):
        mock_own_user = mock.MagicMock(users.OwnUser)
        assert cache_impl.set_me(mock_own_user) is None

    def test_update_me_for_cached_me(self, cache_impl):
        mock_cached_own_user = mock.MagicMock(users.OwnUser)
        mock_own_user = mock.MagicMock(users.OwnUser)
        cache_impl._me = mock_cached_own_user
        assert cache_impl.update_me(mock_own_user) == (mock_cached_own_user, mock_own_user)
        assert cache_impl._me == mock_own_user

    def test_update_me_for_uncached_me(self, cache_impl):
        mock_own_user = mock.MagicMock(users.OwnUser)
        assert cache_impl.update_me(mock_own_user) == (None, mock_own_user)
        assert cache_impl._me == mock_own_user

    def test_clear_members_for_known_member_cache(self, cache_impl):
        ...

    def test_delete_member_for_unknown_guild_record(self, cache_impl):
        assert cache_impl.delete_member(snowflake.Snowflake(42123), snowflake.Snowflake(67876)) is None

    def test_delete_member_for_unknown_member_cache(self, cache_impl):
        cache_impl._guild_entries = {snowflake.Snowflake(42123): stateful_cache._GuildRecord()}
        assert cache_impl.delete_member(snowflake.Snowflake(42123), snowflake.Snowflake(67876)) is None

    def test_delete_member_for_known_member(self, cache_impl):
        mock_member = mock.MagicMock(guilds.Member)
        mock_member_data = mock.MagicMock(stateful_cache._MemberData)
        cache_impl._guild_entries = {
            snowflake.Snowflake(42123): stateful_cache._GuildRecord(
                members={snowflake.Snowflake(67876): mock_member_data}
            )
        }
        cache_impl._build_member = mock.MagicMock(return_value=mock_member)
        assert cache_impl.delete_member(snowflake.Snowflake(42123), snowflake.Snowflake(67876)) is mock_member
        cache_impl._build_member.assert_called_once_with(mock_member_data)

    def test_get_member_for_unknown_member_cache(self, cache_impl):
        cache_impl._guild_entries = {snowflake.Snowflake(1234213): stateful_cache._GuildRecord()}
        assert cache_impl.get_member(snowflake.Snowflake(1234213), snowflake.Snowflake(512312354)) is None

    def test_get_member_for_unknown_guild_record(self, cache_impl):
        assert cache_impl.get_member(snowflake.Snowflake(1234213), snowflake.Snowflake(512312354)) is None

    def test_get_member_for_known_member(self, cache_impl):
        mock_user = mock.MagicMock(users.User)
        member_data = stateful_cache._MemberData(
            id=snowflake.Snowflake(512312354),
            guild_id=snowflake.Snowflake(6434435234),
            nickname="NICK",
            role_ids=(snowflake.Snowflake(65234), snowflake.Snowflake(654234123)),
            joined_at=datetime.datetime(2020, 7, 9, 13, 11, 18, 384554, tzinfo=datetime.timezone.utc),
            premium_since=datetime.datetime(2020, 7, 17, 13, 11, 18, 384554, tzinfo=datetime.timezone.utc),
            is_deaf=False,
            is_mute=True,
        )
        cache_impl._guild_entries = {
            snowflake.Snowflake(1234213): stateful_cache._GuildRecord(
                members={snowflake.Snowflake(512312354): member_data}
            )
        }
        cache_impl._user_entries = {snowflake.Snowflake(512312354): mock_user}
        member = cache_impl.get_member(snowflake.Snowflake(1234213), snowflake.Snowflake(512312354))
        assert member.user == mock_user
        assert member.guild_id == 6434435234
        assert member.nickname == "NICK"
        assert member.role_ids == (snowflake.Snowflake(65234), snowflake.Snowflake(654234123))
        assert member.joined_at == datetime.datetime(2020, 7, 9, 13, 11, 18, 384554, tzinfo=datetime.timezone.utc)
        assert member.premium_since == datetime.datetime(2020, 7, 17, 13, 11, 18, 384554, tzinfo=datetime.timezone.utc)
        assert member.is_deaf is False
        assert member.is_mute is True

    @pytest.mark.asyncio
    async def test_get_members_view_for_unknown_guild_record(self, cache_impl):
        members_mapping = cache_impl.get_members_view(snowflake.Snowflake(42334))
        assert members_mapping == {}

    @pytest.mark.asyncio
    async def test_get_members_view_for_unknown_member_cache(self, cache_impl):
        cache_impl._guild_entries = {snowflake.Snowflake(42334): stateful_cache._GuildRecord()}
        members_mapping = cache_impl.get_members_view(snowflake.Snowflake(42334))
        assert members_mapping == {}

    @pytest.mark.asyncio
    async def test_get_members_view_for_known_guild(self, cache_impl):
        member_data_1 = stateful_cache._MemberData(
            id=snowflake.Snowflake(3214321),
            guild_id=snowflake.Snowflake(54234),
            nickname="a nick",
            role_ids=(snowflake.Snowflake(312123123),),
            joined_at=datetime.datetime(2020, 7, 20, 14, 43, 7, 487015, tzinfo=datetime.timezone.utc),
            premium_since=None,
            is_deaf=True,
            is_mute=False,
        )
        member_data_2 = stateful_cache._MemberData(
            id=snowflake.Snowflake(53224),
            guild_id=snowflake.Snowflake(764345123),
            nickname="OKOK",
            role_ids=tuple(),
            joined_at=datetime.datetime(2020, 7, 20, 14, 43, 7, 65345, tzinfo=datetime.timezone.utc),
            premium_since=datetime.datetime(2020, 7, 15, 14, 43, 7, 487015, tzinfo=datetime.timezone.utc),
            is_deaf=False,
            is_mute=True,
        )
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        guild_record = stateful_cache._GuildRecord(
            members={snowflake.Snowflake(3214321): member_data_1, snowflake.Snowflake(53224): member_data_2,}
        )
        cache_impl._guild_entries = {snowflake.Snowflake(42334): guild_record}
        cache_impl._user_entries = {snowflake.Snowflake(3214321): mock_user_1, snowflake.Snowflake(53224): mock_user_2}
        members_mapping = cache_impl.get_members_view(snowflake.Snowflake(42334))
        assert 3214321 in members_mapping
        current_member = members_mapping[snowflake.Snowflake(3214321)]
        assert current_member.user == mock_user_1
        assert current_member.guild_id == 54234
        assert current_member.nickname == "a nick"
        assert current_member.role_ids == (312123123,)
        assert current_member.joined_at == datetime.datetime(
            2020, 7, 20, 14, 43, 7, 487015, tzinfo=datetime.timezone.utc
        )
        assert current_member.premium_since is None
        assert current_member.is_deaf is True
        assert current_member.is_mute is False
        assert 53224 in members_mapping
        current_member = members_mapping[snowflake.Snowflake(53224)]
        assert current_member.user == mock_user_2
        assert current_member.guild_id == 764345123
        assert current_member.nickname == "OKOK"
        assert current_member.role_ids == tuple()
        assert current_member.joined_at == datetime.datetime(
            2020, 7, 20, 14, 43, 7, 65345, tzinfo=datetime.timezone.utc
        )
        assert current_member.premium_since == datetime.datetime(
            2020, 7, 15, 14, 43, 7, 487015, tzinfo=datetime.timezone.utc
        )
        assert current_member.is_deaf is False
        assert current_member.is_mute is True
        assert len(members_mapping) == 2

    def test_set_member(self, cache_impl):
        mock_user = mock.Mock(users.User, id=snowflake.Snowflake(645234123))
        member_model = guilds.Member()
        member_model.guild_id = snowflake.Snowflake(67345234)
        member_model.user = mock_user
        member_model.nickname = "A NICK LOL"
        member_model.role_ids = (snowflake.Snowflake(65345234), snowflake.Snowflake(123123))
        member_model.joined_at = datetime.datetime(2020, 7, 15, 23, 30, 59, 501602, tzinfo=datetime.timezone.utc)
        member_model.premium_since = datetime.datetime(2020, 7, 1, 2, 0, 12, 501602, tzinfo=datetime.timezone.utc)
        member_model.is_deaf = True
        member_model.is_mute = False
        cache_impl.set_member(member_model)
        assert 67345234 in cache_impl._guild_entries
        assert 645234123 in cache_impl._guild_entries[snowflake.Snowflake(67345234)].members
        member_entry = cache_impl._guild_entries[snowflake.Snowflake(67345234)].members.get(
            snowflake.Snowflake(645234123), ...
        )
        assert member_entry is not ...
        assert member_entry.id == 645234123
        assert member_entry.guild_id == 67345234
        assert member_entry.nickname == "A NICK LOL"
        assert member_entry.role_ids == (65345234, 123123)
        assert member_entry.joined_at == datetime.datetime(
            2020, 7, 15, 23, 30, 59, 501602, tzinfo=datetime.timezone.utc
        )
        assert member_entry.premium_since == datetime.datetime(
            2020, 7, 1, 2, 0, 12, 501602, tzinfo=datetime.timezone.utc
        )
        assert member_entry.is_deaf is True
        assert member_entry.is_mute is False
        assert not hasattr(member_entry, "user")

    def test_update_member(self, cache_impl):
        mock_old_cached_member = mock.MagicMock(guilds.Member)
        mock_new_cached_member = mock.MagicMock(guilds.Member)
        mock_member = mock.MagicMock(
            guilds.Member,
            guild_id=snowflake.Snowflake(123123),
            user=mock.MagicMock(users.User, id=snowflake.Snowflake(65234123)),
        )
        cache_impl.get_member = mock.MagicMock(side_effect=[mock_old_cached_member, mock_new_cached_member])
        cache_impl.set_member = mock.MagicMock()
        assert cache_impl.update_member(mock_member) == (mock_old_cached_member, mock_new_cached_member)
        cache_impl.get_member.assert_has_calls([mock.call(123123, 65234123), mock.call(123123, 65234123)])
        cache_impl.set_member.assert_called_once_with(mock_member)

    def test_clear_users_for_cached_users(self, cache_impl):
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(5432123): mock_user_1,
            snowflake.Snowflake(7654433245): mock_user_2,
        }
        users_mapping = cache_impl.clear_users()
        assert users_mapping == {
            snowflake.Snowflake(5432123): mock_user_1,
            snowflake.Snowflake(7654433245): mock_user_2,
        }
        assert cache_impl._user_entries == {}

    def test_clear_users_for_empty_user_cache(self, cache_impl):
        assert cache_impl.clear_users() == {}
        assert cache_impl._user_entries == {}

    def test_delete_user_for_known_user(self, cache_impl):
        mock_user = mock.MagicMock(users.User)
        mock_other_user = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(21231234): mock_user,
            snowflake.Snowflake(645234): mock_other_user,
        }
        assert cache_impl.delete_user(snowflake.Snowflake(21231234)) is mock_user
        assert cache_impl._user_entries == {snowflake.Snowflake(645234): mock_other_user}

    def test_delete_user_for_unknown_user(self, cache_impl):
        mock_user = mock.MagicMock(users.User)
        mock_other_user = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(21231234): mock_user,
            snowflake.Snowflake(645234): mock_other_user,
        }
        assert cache_impl.delete_user(snowflake.Snowflake(75423423)) is None
        assert cache_impl._user_entries == {
            snowflake.Snowflake(21231234): mock_user,
            snowflake.Snowflake(645234): mock_other_user,
        }

    def test_get_user_for_known_user(self, cache_impl):
        mock_user = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(21231234): mock_user,
            snowflake.Snowflake(645234): mock.MagicMock(users.User),
        }
        assert cache_impl.get_user(snowflake.Snowflake(21231234)) == mock_user

    def test_get_users_view_for_filled_user_cache(self, cache_impl):
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._user_entries = {snowflake.Snowflake(54123): mock_user_1, snowflake.Snowflake(76345): mock_user_2}
        assert cache_impl.get_users_view() == {
            snowflake.Snowflake(54123): mock_user_1,
            snowflake.Snowflake(76345): mock_user_2,
        }

    def test_get_users_view_for_empty_user_cache(self, cache_impl):
        assert cache_impl.get_users_view() == {}

    def test_set_user(self, cache_impl):
        mock_user = mock.MagicMock(users.User, id=snowflake.Snowflake(6451234123))
        mock_cached_user = mock.MagicMock(users.User)
        cache_impl._user_entries = {snowflake.Snowflake(542143): mock_cached_user}
        assert cache_impl.set_user(mock_user) is None
        assert cache_impl._user_entries == {
            snowflake.Snowflake(542143): mock_cached_user,
            snowflake.Snowflake(6451234123): mock_user,
        }

    def test_update_user(self, cache_impl):
        mock_old_cached_user = mock.MagicMock(users.User)
        mock_new_cached_user = mock.MagicMock(users.User)
        mock_user = mock.MagicMock(users.User, id=snowflake.Snowflake(54123123))
        cache_impl.get_user = mock.MagicMock(side_effect=(mock_old_cached_user, mock_new_cached_user))
        cache_impl.set_user = mock.MagicMock()
        assert cache_impl.update_user(mock_user) == (mock_old_cached_user, mock_new_cached_user)
        cache_impl.set_user.assert_called_once_with(mock_user)
        cache_impl.get_user.assert_has_calls([mock.call(54123123), mock.call(54123123)])

    @pytest.mark.skip(reason="todo")  # TODO: this test case
    def test_clear_voice_states(self, cache_impl):
        voice_data_1 = stateful_cache._VoiceStateData(
            channel_id=snowflake.Snowflake(4651234123),
            guild_id=snowflake.Snowflake(54123123),
            is_guild_deafened=True,
            is_guild_muted=False,
            is_self_deafened=True,
            is_self_muted=True,
            is_streaming=False,
            is_suppressed=False,
            is_video_enabled=False,
            user_id=snowflake.Snowflake(7512312),
            session_id="lkmdfslkmfdskjlfsdkjlsfdkjldsf",
        )
        voice_data_2 = stateful_cache._VoiceStateData(
            channel_id=snowflake.Snowflake(542134123),
            guild_id=snowflake.Snowflake(54123123),
            is_guild_deafened=False,
            is_guild_muted=False,
            is_self_deafened=True,
            is_self_muted=True,
            is_streaming=True,
            is_suppressed=False,
            is_video_enabled=False,
            user_id=snowflake.Snowflake(43123123),
            session_id="oeroewrowerkosfdkl",
        )
        member_data_1 = stateful_cache._MemberData(
            id=snowflake.Snowflake(7512312),
            guild_id=snowflake.Snowflake(54123123),
            nickname="blam",
            role_ids=tuple(),
            joined_at=datetime.datetime(2020, 7, 11, 20, 51, 7, 295496, tzinfo=datetime.timezone.utc),
            premium_since=datetime.datetime(2020, 7, 21, 20, 51, 7, 295496, tzinfo=datetime.timezone.utc),
            is_mute=True,
            is_deaf=False,
        )
        member_data_2 = stateful_cache._MemberData(
            id=snowflake.Snowflake(43123123),
            guild_id=snowflake.Snowflake(54123123),
            nickname=None,
            role_ids=(snowflake.Snowflake(543123)),
            joined_at=datetime.datetime(2020, 7, 10, 20, 51, 7, 295496, tzinfo=datetime.timezone.utc),
            premium_since=None,
            is_deaf=True,
            is_mute=False,
        )
        record = stateful_cache._GuildRecord(
            voice_statuses={snowflake.Snowflake(7512312): voice_data_1, snowflake.Snowflake(43123123): voice_data_2},
            members={snowflake.Snowflake(7512312): member_data_1, snowflake.Snowflake(43123123): member_data_2},
        )
        mock_user_1 = mock.MagicMock(users.User)
        mock_user_2 = mock.MagicMock(users.User)
        cache_impl._user_entries = {
            snowflake.Snowflake(7512312): mock_user_1,
            snowflake.Snowflake(43123123): mock_user_2,
        }
        cache_impl._guild_entries = {snowflake.Snowflake(54123123): record}
        voice_state_mapping = cache_impl.clear_voice_states(snowflake.Snowflake(54123123))
        assert 7512312 in voice_state_mapping
        current_voice_state = voice_state_mapping[snowflake.Snowflake(7512312)]
        assert current_voice_state
        assert 43123123 in voice_state_mapping
        current_voice_state = voice_state_mapping[snowflake.Snowflake(43123123)]
        assert current_voice_state
        assert len(voice_state_mapping) == 2

    @pytest.mark.skip(reason="todo")
    def test_delete_voice_state(self, cache_impl):
        ...

    @pytest.mark.skip(reason="todo")
    def test_get_voice_state(self, cache_impl):
        ...

    @pytest.mark.skip(reason="todo")
    def test_get_voice_state_view(self, cache_impl):
        ...

    @pytest.mark.skip(reason="todo")
    def test_set_voice_state(self, cache_impl):
        ...

    @pytest.mark.skip(reason="todo")
    def test_update_voice_state(self, cache_impl):
        ...
