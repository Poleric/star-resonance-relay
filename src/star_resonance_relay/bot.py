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
from star_resonance_relay.proto.enum_place_holder_type_pb2 import PlaceHolderType
from star_resonance_relay.proto.serv_chit_chat_ntf_pb2 import ChitChatNtf
from star_resonance_relay.proto.serv_social_pb2 import Social
from star_resonance_relay.proto.stru_notify_newest_chit_chat_msgs_request_pb2 import NotifyNewestChitChatMsgsRequest
from star_resonance_relay.proto.stru_place_holder_buff_pb2 import PlaceHolderBuff
from star_resonance_relay.proto.stru_place_holder_fish_item_pb2 import PlaceHolderFishItem
from star_resonance_relay.proto.stru_place_holder_fish_personal_total_pb2 import PlaceHolderFishPersonalTotal
from star_resonance_relay.proto.stru_place_holder_fish_rank_pb2 import PlaceHolderFishRank
from star_resonance_relay.proto.stru_place_holder_item_pb2 import PlaceHolderItem
from star_resonance_relay.proto.stru_place_holder_master_mode_pb2 import PlaceHolderMasterMode
from star_resonance_relay.proto.stru_place_holder_pb2 import PlaceHolder
from star_resonance_relay.proto.stru_place_holder_player_pb2 import PlaceHolderPlayer
from star_resonance_relay.proto.stru_place_holder_scene_position_pb2 import PlaceHolderScenePosition
from star_resonance_relay.proto.stru_place_holder_str_pb2 import PlaceHolderStr
from star_resonance_relay.proto.stru_place_holder_timestamp_pb2 import PlaceHolderTimestamp
from star_resonance_relay.proto.stru_place_holder_union_pb2 import PlaceHolderUnion
from star_resonance_relay.proto.stru_place_holder_val_pb2 import PlaceHolderVal
from star_resonance_relay.sniffer.sniffer import BPSRSniffer

logger = logging.getLogger(__name__)

# in_game_id: discord_emoji
EMOJI_MAPPING: dict[str, str] = {
    "<sprite=1>": ":grin:",
    "<sprite=2>": ":joy:",
    "<sprite=3>": ":smiley:",
    "<sprite=4>": ":smile:",
    "<sprite=5>": ":sweat_smile:",
    "<sprite=6>": ":laughing:",
    "<sprite=7>": ":innocent:",
    "<sprite=8>": ":smiling_imp:",
    "<sprite=9>": ":wink:",
    "<sprite=10>": ":neutral_face:",
    "<sprite=11>": ":expressionless:",
    "<sprite=12>": ":unamused:",
    "<sprite=13>": ":sweat:",
    "<sprite=14>": ":pensive:",
    "<sprite=15>": ":confused:",
    "<sprite=16>": ":confounded:",
    "<sprite=17>": ":kissing:",
    "<sprite=18>": ":kissing_heart:",
    "<sprite=19>": ":kissing_smiling_eyes:",
    "<sprite=20>": ":angry:",
    "<sprite=21>": ":rage:",
    "<sprite=22>": ":cry:",
    "<sprite=23>": ":persevere:",
    "<sprite=24>": ":triumph:",
    "<sprite=25>": ":disappointed_relieved:",
    "<sprite=26>": ":frowning:",
    "<sprite=27>": ":anguished:",
    "<sprite=28>": ":fearful:",
    "<sprite=29>": ":weary:",
    "<sprite=30>": ":cold_sweat:",
    "<sprite=31>": ":scream:",
    "<sprite=32>": ":astonished:",
    "<sprite=33>": ":flushed:",
    "<sprite=34>": ":sleeping:",
    "<sprite=35>": ":dizzy_face:",
    "<sprite=36>": ":no_mouth:",
    "<sprite=37>": ":mask:",
    "<sprite=38>": ":slight_frown:",
    "<sprite=39>": ":slight_smile:",
    "<sprite=40>": ":upside_down:",
    "<sprite=41>": ":rolling_eyes:",
    "<sprite=42>": ":blush:",
    "<sprite=43>": ":yum:",
    "<sprite=44>": ":relieved:",
    "<sprite=45>": ":heart_eyes:",
    "<sprite=46>": ":sunglasses:",
    "<sprite=47>": ":smirk:",
    "<sprite=48>": ":kissing_closed_eyes:",
    "<sprite=49>": ":stuck_out_tongue:",
    "<sprite=50>": ":stuck_out_tongue_winking_eye:",
    "<sprite=51>": ":stuck_out_tongue_closed_eye:",
    "<sprite=52>": ":disappointed:",
    "<sprite=53>": ":worried:",
    "<sprite=54>": ":sleepy:",
    "<sprite=55>": ":tired_face:",
    "<sprite=56>": ":grimacing:",
    "<sprite=57>": ":sob:",
    "<sprite=58>": ":open_mouth:",
    "<sprite=59>": ":hushed:",
    "<sprite=60>": ":smiley_cat:",
    "<sprite=61>": ":smirk_cat:",
    "<sprite=62>": ":kissing_cat:",
    "<sprite=63>": ":pouting_cat:",
}

# config_id: discord_sticker
PICTURE_EMOJI_MAPPING: dict[int, str] = {
    3001: "",
    3002: "",
    3003: "",
    3004: "",
    3005: "",
    3006: "",
    3007: "",
    3008: "",
    3009: "",
    3010: "",
    3011: "",
    3012: "",
    3013: "",
    3014: "",
    3015: "",
    6001: "",
    6002: "",
    6003: "",
    6004: "",
    6005: "",
    6006: "",
    6007: "",
    6008: "",
    6009: "",
    6010: "",
    6011: "",
    6012: "",
    6013: "",
    6014: "",
    6015: "",
    6016: "",
    6017: "",
    6018: "",
    6019: "",
    6020: "",
    6021: "",
    6022: "",
    6023: "",
    6024: "",
    6025: "",
    6026: "",
    6027: "",
    6028: "",
    6029: "",
    6030: "",
    6031: "",
    6032: "",
    6033: "",
    6034: "",
    6035: "",
    6036: "",
    6037: "",
    6038: "",
    6039: "",
    6040: "",
    8001: "<:Olvera1:1459802030431404147>",
    8002: "<:Olvera2:1459802099809517669>",
    8003: "<:Olvera3:1459802216264237096>",
    8004: "<:Airona0:1459800579047031000>",
    8005: "<:Airona1:1459800681249509376>",
    8006: "<:Airona3:1459800756054917285>",
    8007: "<:Jerard1:1459801872419258411>",
    8008: "<:Jerard2:1459801911925538830>",
    8009: "<:Tina1:1459802279015092224>",
    8010: "<:Tina2:1459802321881141259>",
    8011: "<:Tina3:1459815311623852045>",
    8012: "<:Jerard3:1459801959111589889>",
    9001: "",
    9002: "",
    9003: "",
    9004: "",
    9005: "",
    9006: "",
    9007: "",
    9008: "",
    9009: "",
    9010: "",
    9011: "",
    10001: "",
    10002: "",
    10003: "",
    10004: "",
    10005: "",
    10006: "",
    10007: "",
    10008: "",
    10009: "",
    10010: "",
    10011: "",
    10012: "",
    12001: "",
    12002: "",
    12003: "",
    12004: "",
    12005: "",
    12006: "",
    12007: "",
    11001: "<:ThumbsUp:1377207065117986856>",
    11002: "<:Love:1380650608129736795>",
    11003: "<:LetsGo:1380650591214239806>",
    11004: "<:Loading:1377206042806452255>",
    11005: "<:Blushing:1377206036829569054>",
    11006: "<:Proud2:1377206785919684669>",
    11007: "<:Drolling:1380650068045992078>",
    11008: "<:WhatMe:1377206047445487707>",
    11009: "<:WhatIsThis:1380649841297985546>",
    11010: "<:Tehehe:1380651342246318150>",
    11011: "<:Evil:1377206039912644758>",
    11012: "<:Unconscious:1377206045507846196>",
    11013: "<:Crying:1380650225492037754>",
}

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


class HypertextVariant(Enum):
    ITEM_SHARING = 3000001
    MASTER_SEAL = 1050001
    PERSONAL_SPACE = 3001001
    FISH = 8009003
    FISHING_RECORD = 8009005
    GUILD_WELCOME_NEW_MEMBER = 5001012
    GUILD_HUNT_PROGRESS = 5010003
    EE_CHAN = 1005003


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
    PLACEHOLDER_MAPPING: dict[PlaceHolderType, type[Message]] = {
        PlaceHolderType.PlaceHolderTypeVal: PlaceHolderVal,
        PlaceHolderType.PlaceHolderTypePlayer: PlaceHolderPlayer,
        PlaceHolderType.PlaceHolderTypeItem: PlaceHolderItem,
        PlaceHolderType.PlaceHolderTypeUnion: PlaceHolderUnion,
        PlaceHolderType.PlaceHolderTypeBuff: PlaceHolderBuff,
        PlaceHolderType.PlaceHolderTypeTimestamp: PlaceHolderTimestamp,
        PlaceHolderType.PlaceHolderTypeString: PlaceHolderStr,
        PlaceHolderType.PlaceHolderTypeFishPersonalTotal: PlaceHolderFishPersonalTotal,
        PlaceHolderType.PlaceHolderTypeFishItem: PlaceHolderFishItem,
        PlaceHolderType.PlaceHolderTypeFishRank: PlaceHolderFishRank,
        PlaceHolderType.PlaceHolderTypeMasterMode: PlaceHolderMasterMode,
        PlaceHolderType.PlaceHolderTypeScenePosition: PlaceHolderScenePosition,
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

    def _decode_placeholder(self, placeholder: PlaceHolder) -> (
            PlaceHolderVal
            | PlaceHolderPlayer
            | PlaceHolderItem
            | PlaceHolderUnion
            | PlaceHolderBuff
            | PlaceHolderTimestamp
            | PlaceHolderStr
            | PlaceHolderFishPersonalTotal
            | PlaceHolderFishItem
            | PlaceHolderFishRank
            | PlaceHolderMasterMode
            | PlaceHolderScenePosition):
        decoder = self.PLACEHOLDER_MAPPING.get(placeholder.type)
        if decoder is None:
            raise NotImplementedError

        try:
            # All compiled protobuf messages support ``FromString``
            return decoder.FromString(placeholder.bytes_content)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to decode %s: %s", placeholder, exc)
            raise

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
                    placeholder_content = self._decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderItem() as item:
                            content += f"[ __{get_item_name(item.config_id) or item.config_id}__ ]"

            case HypertextVariant.MASTER_SEAL:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = self._decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderMasterMode() as master:
                            content += f"[ __{master.user_name}'s Master Seal__ ]"

            case HypertextVariant.PERSONAL_SPACE:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = self._decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderPlayer() as player:
                            content += f"[ __{player.name}'s personal space__ ]"

            case HypertextVariant.FISH:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = self._decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishItem() as fish:
                            content += f"[ __{event.chat_msg.send_char_info.name}'s record of {get_item_name(fish.fish_id) or fish.fish_id}__ ]"

            case HypertextVariant.FISHING_RECORD:
                username = self._get_player_header(event)
                content = ""

                for placeholder in hypertext.hypertext_contents:
                    placeholder_content = self._decode_placeholder(placeholder)
                    match placeholder_content:
                        case PlaceHolderStr() as string:
                            content += string.text
                        case PlaceHolderFishPersonalTotal() as record:
                            content += f"[ __{record.user_name}'s fishing profile__ ]"

            case HypertextVariant.GUILD_WELCOME_NEW_MEMBER:
                placeholder = hypertext.hypertext_contents[0]
                player: PlaceHolderPlayer = self._decode_placeholder(placeholder)

                username = "Guild Administrator"
                content = Embed(description=f"Welcome __{player.name}__ to the Guild!")

            case HypertextVariant.GUILD_HUNT_PROGRESS:
                placeholder = hypertext.hypertext_contents[0]
                value: PlaceHolderVal = self._decode_placeholder(placeholder)

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
