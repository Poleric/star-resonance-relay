import logging
import os
from dataclasses import dataclass
from enum import Enum

import polars as pl
import requests
from discord import SyncWebhook, Embed, SyncWebhookMessage
from discord.utils import MISSING
from google.protobuf.message import Message

from star_resonance_relay.packet import method as MethodId
from star_resonance_relay.packet.service import Service
from star_resonance_relay.proto.enum_chit_chat_channel_type_pb2 import ChitChatChannelType
from star_resonance_relay.proto.enum_chit_chat_msg_type_pb2 import ChitChatMsgType
from star_resonance_relay.proto.serv_chit_chat_ntf_pb2 import ChitChatNtf
from star_resonance_relay.proto.serv_social_pb2 import Social
from star_resonance_relay.proto.stru_notify_newest_chit_chat_msgs_request_pb2 import NotifyNewestChitChatMsgsRequest
from star_resonance_relay.proto.stru_place_holder_fish_item_pb2 import PlaceHolderFishItem
from star_resonance_relay.proto.stru_place_holder_fish_personal_total_pb2 import PlaceHolderFishPersonalTotal
from star_resonance_relay.proto.stru_place_holder_item_pb2 import PlaceHolderItem
from star_resonance_relay.proto.stru_place_holder_master_mode_pb2 import PlaceHolderMasterMode
from star_resonance_relay.proto.stru_place_holder_player_pb2 import PlaceHolderPlayer
from star_resonance_relay.proto.stru_place_holder_str_pb2 import PlaceHolderStr
from star_resonance_relay.placeholder import HypertextVariant, decode_placeholder
from star_resonance_relay.const import PICTURE_EMOJI_MAPPING, EMOJI_MAPPING
from star_resonance_relay.proto.stru_place_holder_val_pb2 import PlaceHolderVal
from star_resonance_relay.sniffer.sniffer import BPSRSniffer

logger = logging.getLogger(__name__)


ITEM_MAPPING = pl.read_json("./ref/StarResonanceData/ztable/ItemTable.json").transpose().unnest()


def get_item_name(item_config_id: int) -> str | None:
    try:
        return ITEM_MAPPING.filter(pl.col.Id == item_config_id).select("Name").item()
    except ValueError:
        return None


@dataclass(slots=True)
class WebhookContent:
    username: str
    content: str | Embed
    avatar_url: str | None

    def send_to(self, webhook: SyncWebhook) -> SyncWebhookMessage | None:
        if isinstance(self.content, Embed):
            return webhook.send(embed=self.content, username=self.username, avatar_url=self.avatar_url or MISSING)
        return webhook.send(self.content, username=self.username, avatar_url=self.avatar_url or MISSING)


class BPSRRelayBot:
    CHANNEL_MAPPING: dict[ChitChatChannelType, str] = {
        ChitChatChannelType.ChannelWorld: "World",
        ChitChatChannelType.ChannelScene: "Current",
        ChitChatChannelType.ChannelTeam: "Team",
        ChitChatChannelType.ChannelUnion: "Guild",
        ChitChatChannelType.ChannelPrivate: "Private",
        ChitChatChannelType.ChannelGroup: "Group",
        ChitChatChannelType.ChannelTopNotice: "Notice",
        ChitChatChannelType.ChannelSystem: "System"
    }

    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL")
        if not self.webhook_url:
            raise RuntimeError("WEBHOOK_URL env is not defined")

        self.channel_types: list[ChitChatChannelType] = []
        self.player_avatar_url: dict[int, str] = {}

        inverse_lookup = {v: k for k, v in self.CHANNEL_MAPPING.items()}
        channel_type_string = os.getenv("CHANNEL_TYPE")
        if not channel_type_string:
            raise RuntimeError("CHANNEL_TYPE env is not defined")

        for key in channel_type_string.split(","):
            channel_type = inverse_lookup.get(key)
            if channel_type:
                self.channel_types.append(channel_type)

        self.webhook = SyncWebhook.from_url(self.webhook_url, session=requests.Session())

        self.sniffer = BPSRSniffer()
        self.sniffer.set_service_type(Service.ChitChatNtf.value, MethodId.ChitChatNtf.NotifyNewestChitChatMsgs.value,
                                      ChitChatNtf.NotifyNewestChitChatMsgs)
        self.sniffer.set_service_type(Service.Social.value, MethodId.Social.GetSocialData.value, Social.GetSocialData)
        self.sniffer.set_return_type(Social.GetSocialData, Social.GetSocialData_Ret)
        self.sniffer.subscribe(Social.GetSocialData_Ret, self.on_get_social_data)
        self.sniffer.subscribe(ChitChatNtf.NotifyNewestChitChatMsgs, self.on_chit_chat_msg)

        logger.info(f"Connected to webhook {self.webhook}")

    def start(self) -> None:
        self.sniffer.sniff()
        logger.info("Started sniffing")

    def on_get_social_data(self, event: Social.GetSocialData_Ret) -> None:
        data = event.ret.data
        self.player_avatar_url[data.char_id] = data.avatar_info.profile.url
        logger.info(f"Saved {data.char_id} profile image")

    def on_chit_chat_msg(self, event: ChitChatNtf.NotifyNewestChitChatMsgs) -> None:
        req = event.v_request
        content: WebhookContent | None = None
        match req.chat_msg.msg_info.msg_type:
            case ChitChatMsgType.ChatMsgTextMessage:
                content = self._process_text_message(req)
            case ChitChatMsgType.ChatMsgPictureEmoji:
                content = self._process_picture_emoji(req)
            case ChitChatMsgType.ChatMsgHypertext:
                try:
                    content = self._process_hypertext(req)
                except NotImplementedError:
                    pass

        if content:
            logger.info(f"{content=}")

            content.send_to(self.webhook)
        else:
            logger.info(event)

    def _get_player_header(self, event: NotifyNewestChitChatMsgsRequest) -> str:
        char_info = event.chat_msg.send_char_info

        return "{name}{sprout}[{channel}]".format(
            name=char_info.name,
            sprout=" 🌱 " if char_info.is_newbie else " ",
            channel=self.CHANNEL_MAPPING[event.channel_type]
        )

    def _process_text_message(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        content = event.chat_msg.msg_info.msg_text

        for key, value in EMOJI_MAPPING.items():
            content = content.replace(key, value)

        return WebhookContent(
            username=self._get_player_header(event),
            content=content,
            avatar_url=self.player_avatar_url.get(event.chat_msg.send_char_info.char_id)
        )

    def _process_picture_emoji(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        emoji = PICTURE_EMOJI_MAPPING.get(event.chat_msg.msg_info.picture_emoji.config_id)
        if emoji is None:
            raise NotImplementedError

        return WebhookContent(
            username=self._get_player_header(event),
            content=emoji,
            avatar_url=self.player_avatar_url.get(event.chat_msg.send_char_info.char_id)
        )

    def _process_hypertext(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        hypertext = event.chat_msg.msg_info.chat_hypertext
        try:
            hypertext_type = HypertextVariant(hypertext.config_id)
        except ValueError:
            raise NotImplementedError

        match hypertext_type:
            case HypertextVariant.ITEM_SHARING:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderItem() as item:
                            content += f"[ __{get_item_name(item.config_id) or item.config_id}__ ]"

            case HypertextVariant.MASTER_SEAL:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderMasterMode() as master:
                            content += f"[ __{master.user_name}'s Master Seal__ ]"

            case HypertextVariant.PERSONAL_SPACE:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderPlayer() as player:
                            content += f"[ __{player.name}'s personal space__ ]"

            case HypertextVariant.FISH:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishItem() as fish:
                            content += f"[ __{event.chat_msg.send_char_info.name}'s record of {get_item_name(fish.fish_id) or fish.fish_id}__ ]"

            case HypertextVariant.FISHING_RECORD:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishPersonalTotal() as record:
                            content += f"[ __{record.user_name}'s fishing profile__ ]"

            case HypertextVariant.GUILD_WELCOME_NEW_MEMBER:
                placeholder = hypertext.hypertext_contents[0]
                player: PlaceHolderPlayer = decode_placeholder(placeholder)

                username = "Guild Administrator"
                content = Embed(description=f"Welcome __{player.name}__ to the Guild!")

            case HypertextVariant.GUILD_HUNT_PROGRESS:
                placeholder = hypertext.hypertext_contents[0]
                value: PlaceHolderVal = decode_placeholder(placeholder)

                username = "Guild"
                content = Embed(
                    description=f"With everyone's active participation, the hunting progress has reach {value.value}%, you can open the event interface to receive additional rewards provided by the Pioneer Bureau")

            case HypertextVariant.EE_CHAN:
                username = "Guild"
                content = Embed(
                    description="Ee-chan has brought rewards to the Guild, come and find Ee-chan to claim your rewards~")

            case _:
                raise NotImplementedError

        return WebhookContent(
            username=username,
            content=content,
            avatar_url=self.player_avatar_url.get(event.chat_msg.send_char_info.char_id)
        )


def main():
    from discord.utils import setup_logging

    setup_logging()

    bot = BPSRRelayBot()
    bot.start()


if __name__ == '__main__':
    main()
