import dbm
import logging
import os
from dataclasses import dataclass
from typing import Self

import requests
from discord import SyncWebhook, Embed, SyncWebhookMessage
from discord.utils import MISSING
from scapy.config import conf
from scapy.layers.inet import TCP, IP
from scapy.packet import Packet, Raw
from scapy.sendrecv import sniff
from star_resonance_tracer.proto.enum_chit_chat_channel_type_pb2 import ChitChatChannelType
from star_resonance_tracer.proto.enum_chit_chat_msg_type_pb2 import ChitChatMsgType
from star_resonance_tracer.proto.serv_chit_chat_ntf_pb2 import ChitChatNtf as ChitChatNtfPb
from star_resonance_tracer.proto.serv_social_pb2 import Social as SocialPb
from star_resonance_tracer.proto.stru_notify_newest_chit_chat_msgs_request_pb2 import NotifyNewestChitChatMsgsRequest
from star_resonance_tracer.proto.stru_place_holder_fish_item_pb2 import PlaceHolderFishItem
from star_resonance_tracer.proto.stru_place_holder_fish_personal_total_pb2 import PlaceHolderFishPersonalTotal
from star_resonance_tracer.proto.stru_place_holder_item_pb2 import PlaceHolderItem
from star_resonance_tracer.proto.stru_place_holder_master_mode_pb2 import PlaceHolderMasterMode
from star_resonance_tracer.proto.stru_place_holder_player_pb2 import PlaceHolderPlayer
from star_resonance_tracer.proto.stru_place_holder_str_pb2 import PlaceHolderStr
from star_resonance_tracer.proto.stru_place_holder_val_pb2 import PlaceHolderVal
from star_resonance_tracer.sniffer import Sniffer, Connection

from star_resonance_relay.const.emoji import PICTURE_EMOJI_MAPPING, EMOJI_MAPPING
from star_resonance_relay.const.item import get_item_name
from star_resonance_relay.const.placeholder import HypertextVariant, decode_placeholder
from star_resonance_relay.const.service import ChitChatNtf, Social

logger = logging.getLogger(__name__)

conf.layers.filter([TCP, IP])


def get_env_or_raise(key: str) -> str:
    env = os.getenv(key)
    if not env:
        raise RuntimeError(f"{key} env is not defined")
    return env


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
    CHANNEL_TYPE_TO_NAME: dict[ChitChatChannelType, str] = {
        ChitChatChannelType.ChannelWorld: "World",
        ChitChatChannelType.ChannelScene: "Current",
        ChitChatChannelType.ChannelTeam: "Team",
        ChitChatChannelType.ChannelUnion: "Guild",
        ChitChatChannelType.ChannelPrivate: "Private",
        ChitChatChannelType.ChannelGroup: "Group",
        ChitChatChannelType.ChannelTopNotice: "Notice",
        ChitChatChannelType.ChannelSystem: "System"
    }
    CHANNEL_NAME_TO_TYPE: dict[str, ChitChatChannelType] = {v: k for k, v in CHANNEL_TYPE_TO_NAME.items()}

    def __init__(self):
        self.webhook_url = get_env_or_raise("WEBHOOK_URL")
        self.channel_types: list[ChitChatChannelType] = [self.CHANNEL_NAME_TO_TYPE[key]
                                                         for key in get_env_or_raise("CHANNEL_TYPE").split(",")
                                                         if key in self.CHANNEL_NAME_TO_TYPE]
        self.player_avatar_url = dbm.open(get_env_or_raise("CACHE_FILE"), "c")

        self.webhook = SyncWebhook.from_url(self.webhook_url, session=requests.Session())
        logger.info(f"Connected to webhook {self.webhook}")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.player_avatar_url.close()

    def start(self) -> None:
        sniffer = Sniffer()
        sniffer.set_service_type(ChitChatNtf.ServiceId.value, ChitChatNtf.Method.NotifyNewestChitChatMsgs.value,
                                 ChitChatNtfPb.NotifyNewestChitChatMsgs)
        sniffer.set_service_type(Social.ServiceId.value, Social.Method.GetSocialData.value, SocialPb.GetSocialData)
        sniffer.set_return_type(SocialPb.GetSocialData, SocialPb.GetSocialData_Ret)
        sniffer.on_service(SocialPb.GetSocialData_Ret, self.on_get_social_data)
        sniffer.on_service(ChitChatNtfPb.NotifyNewestChitChatMsgs, self.on_chit_chat_msg)

        def on_packet(packet: Packet) -> None:
            if TCP not in packet or Raw not in packet:
                return

            tcp = packet[TCP]
            ip = packet[IP]

            connection = Connection.from_tuple(ip.src, tcp.sport, ip.dst, tcp.dport)

            payload = bytes(packet[Raw])

            sniffer.process_packet(connection, payload, tcp_sequence=tcp.seq)

        logger.info("Started sniffing")
        sniff(filter="tcp and ip", prn=on_packet, store=False)

    def on_get_social_data(self, event: SocialPb.GetSocialData_Ret) -> None:
        data = event.ret.data
        self._save_player_avatar(data.charId, data.avatarInfo.profile.url)
        logger.info(f"Saved {data.charId} profile image")

    def on_chit_chat_msg(self, event: ChitChatNtfPb.NotifyNewestChitChatMsgs) -> None:
        req = event.vRequest
        if req.channelType not in self.channel_types:
            return

        content: WebhookContent | None = None
        match req.chatMsg.msgInfo.msgType:
            case ChitChatMsgType.ChatMsgTextMessage:
                content = self._process_text_message(req)
            case ChitChatMsgType.ChatMsgPictureEmoji:
                try:
                    content = self._process_picture_emoji(req)
                except NotImplementedError:
                    pass
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

    def _save_player_avatar(self, player_id: int, avatar_url: str) -> None:
        self.player_avatar_url[player_id.to_bytes(length=8)] = avatar_url.encode()

    def _get_player_avatar(self, player_id: int) -> str | None:
        result = self.player_avatar_url.get(player_id.to_bytes(length=8))
        if not result:
            return None
        return result.decode()

    def _get_player_header(self, event: NotifyNewestChitChatMsgsRequest) -> str:
        char_info = event.chatMsg.sendCharInfo

        return "{name}{sprout}[{channel}]".format(
            name=char_info.name,
            sprout=" 🌱 " if char_info.isNewbie else " ",
            channel=self.CHANNEL_TYPE_TO_NAME[event.channelType]
        )

    def _process_text_message(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        content = event.chatMsg.msgInfo.msgText

        for key, value in EMOJI_MAPPING.items():
            content = content.replace(key, value)

        return WebhookContent(
            username=self._get_player_header(event),
            content=content,
            avatar_url=self._get_player_avatar(event.chatMsg.sendCharInfo.charID)
        )

    def _process_picture_emoji(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        emoji = PICTURE_EMOJI_MAPPING.get(event.chatMsg.msgInfo.pictureEmoji.configId)
        if not emoji:
            raise NotImplementedError

        return WebhookContent(
            username=self._get_player_header(event),
            content=emoji,
            avatar_url=self._get_player_avatar(event.chatMsg.sendCharInfo.charID)
        )

    def _process_hypertext(self, event: NotifyNewestChitChatMsgsRequest) -> WebhookContent:
        hypertext = event.chatMsg.msgInfo.chatHypertext
        try:
            hypertext_type = HypertextVariant(hypertext.configId)
        except ValueError:
            raise NotImplementedError

        match hypertext_type:
            case HypertextVariant.ITEM_SHARING:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertextContents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderItem() as item:
                            content += f"[ __{get_item_name(item.configId) or item.configId}__ ]"

            case HypertextVariant.MASTER_SEAL:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertextContents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderMasterMode() as master:
                            content += f"[ __{master.userName}'s Master Seal__ ]"

            case HypertextVariant.PERSONAL_SPACE:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertextContents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderPlayer() as player:
                            content += f"[ __{player.name}'s personal space__ ]"

            case HypertextVariant.FISH:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertextContents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishItem() as fish:
                            content += f"[ __{event.chatMsg.sendCharInfo.name}'s record of {get_item_name(fish.FishId) or fish.FishId}__ ]"

            case HypertextVariant.FISHING_RECORD:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertextContents:
                    placeholder_content = decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishPersonalTotal() as record:
                            content += f"[ __{record.userName}'s fishing profile__ ]"

            case HypertextVariant.GUILD_WELCOME_NEW_MEMBER:
                placeholder = hypertext.hypertextContents[0]
                player: PlaceHolderPlayer = decode_placeholder(placeholder)

                username = "Guild Administrator"
                content = Embed(description=f"Welcome __{player.name}__ to the Guild!")

            case HypertextVariant.GUILD_HUNT_PROGRESS:
                placeholder = hypertext.hypertextContents[0]
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
            avatar_url=self._get_player_avatar(event.chatMsg.sendCharInfo.charID)
        )


def main():
    from discord.utils import setup_logging

    setup_logging()

    with BPSRRelayBot() as bot:
        bot.start()


if __name__ == '__main__':
    main()
