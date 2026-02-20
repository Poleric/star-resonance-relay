import logging
import os

import requests
from discord import Intents, SyncWebhook
from discord.ext.commands import Bot
from google.protobuf.message import Message
from scapy.sendrecv import AsyncSniffer

from star_resonance_relay.proto.serv_chit_chat_ntf_pb2 import ChitChatNtf
from star_resonance_relay.proto.enum_chit_chat_channel_type_pb2 import ChitChatChannelType
from star_resonance_relay.proto.enum_chit_chat_msg_type_pb2 import ChitChatMsgType
from star_resonance_relay.proto.stru_chit_chat_msg_pb2 import ChitChatMsg
from star_resonance_relay.proto.stru_place_holder_pb2 import PlaceHolder
from star_resonance_relay.proto.enum_place_holder_type_pb2 import PlaceHolderType
from star_resonance_relay.proto.stru_place_holder_val_pb2 import PlaceHolderVal
from star_resonance_relay.proto.stru_place_holder_player_pb2 import PlaceHolderPlayer
from star_resonance_relay.proto.stru_place_holder_item_pb2 import PlaceHolderItem
from star_resonance_relay.proto.stru_place_holder_buff_pb2 import PlaceHolderBuff
from star_resonance_relay.proto.stru_place_holder_timestamp_pb2 import PlaceHolderTimestamp
from star_resonance_relay.proto.stru_place_holder_str_pb2 import PlaceHolderStr
from star_resonance_relay.proto.stru_place_holder_fish_personal_total_pb2 import PlaceHolderFishPersonalTotal
from star_resonance_relay.proto.stru_place_holder_fish_item_pb2 import PlaceHolderFishItem
from star_resonance_relay.proto.stru_place_holder_fish_rank_pb2 import PlaceHolderFishRank
from star_resonance_relay.proto.stru_place_holder_union_pb2 import PlaceHolderUnion
from star_resonance_relay.proto.stru_place_holder_master_mode_pb2 import PlaceHolderMasterMode
from star_resonance_relay.proto.stru_place_holder_scene_position_pb2 import PlaceHolderScenePosition
from star_resonance_relay.const.item import ITEM_NAME_MAPPING
from star_resonance_relay.sniffer import BPSRChatSniffer

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
    "<sprite=18>": ":kissing_hear:",
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
    8001: ":Olvera1:",
    8002: ":Olvera2:",
    8003: ":Olvera3:",
    8004: ":Airona1:",
    8005: ":Airona2:",
    8006: ":Airona3:",
    8007: ":Jerard1:",
    8008: ":Jerard2:",
    8009: ":Tina1:",
    8010: ":Tina2:",
    8011: ":Tina3:",
    8012: ":Jerard3:",
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
    11001: ":Airona4:",
    11002: ":Airona5:",
    11003: ":Airona6:",
    11004: ":Airona7:",
    11005: ":Airona8:",
    11006: ":Airona9:",
    11007: ":Airona10:",
    11008: ":Airona11:",
    11009: ":Airona12:",
    11010: ":Airona13:",
    11011: ":Airona14:",
    11012: ":Airona15:",
    11013: ":Airona16:",
}

class BPSRRelayBot(Bot):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.channel_types: list[ChitChatChannelType] = []

        inverse_lookup = {v: k for k, v in self.CHANNEL_MAPPING.items()}
        for key in os.getenv("CHANNEL_TYPE").split(","):
            channel_type = inverse_lookup.get(key)
            if channel_type:
                self.channel_types.append(channel_type)

        self.listener = BPSRChatSniffer(self.on_bpsr_message)
        self.session = requests.Session()

        self.sniffer = AsyncSniffer(prn=lambda pkt: self.listener.handle_packet(pkt), store=False)
        self.sniffer.start()

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

    def on_bpsr_message(self, payload: Message) -> None:
        if not isinstance(payload, ChitChatNtf.NotifyNewestChitChatMsgs):
            return

        payload: ChitChatNtf.NotifyNewestChitChatMsgs

        channel = payload.v_request.channel_type
        if channel not in self.channel_types:
            return

        message = payload.v_request.chat_msg
        self.send_message(
            channel,
            message
        )

    def send_message(self, channel_type: ChitChatChannelType, message: ChitChatMsg):
        msg_info = message.msg_info
        char_info = message.send_char_info

        header: str | None = None
        content: str | None = None
        match msg_info.msg_type:
            case ChitChatMsgType.ChatMsgTextMessage:
                header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                content = msg_info.msg_text

                for key, value in EMOJI_MAPPING.items():
                    content = content.replace(key, value)
            case ChitChatMsgType.ChatMsgPictureEmoji:
                header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                content = PICTURE_EMOJI_MAPPING.get(msg_info.picture_emoji.config_id)
            case ChitChatMsgType.ChatMsgHypertext:
                hypertext = msg_info.chat_hypertext
                match hypertext.config_id:
                    case 3000001:  # normal chatting
                        header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                        content = ""

                        for placeholder in hypertext.hypertext_contents:
                            placeholder_content = self._decode_placeholder(placeholder)
                            match placeholder_content:
                                case PlaceHolderStr() as string:
                                    content += string.text
                                case PlaceHolderItem() as item:
                                    content += f"[ __{ITEM_NAME_MAPPING.get(item.config_id, item.config_id)}__ ]"

                    case 1050001:  # sharing master seal
                        header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                        content = ""

                        for placeholder in hypertext.hypertext_contents:
                            placeholder_content = self._decode_placeholder(placeholder)
                            match placeholder_content:
                                case PlaceHolderStr() as string:
                                    content += string.text
                                case PlaceHolderMasterMode() as master:
                                    content += f"[ __{master.user_name}'s Master Seal__ ]"

                    case 3001001:  # sharing personal space
                        header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                        content = ""

                        for placeholder in hypertext.hypertext_contents:
                            placeholder_content = self._decode_placeholder(placeholder)
                            match placeholder_content:
                                case PlaceHolderStr() as string:
                                    content += string.text
                                case PlaceHolderPlayer() as player:
                                    content += f"[ __{player.name}'s personal space__ ]"

                    case 8009003:  # sharing fish
                        header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                        content = ""

                        for placeholder in hypertext.hypertext_contents:
                            placeholder_content = self._decode_placeholder(placeholder)
                            match placeholder_content:
                                case PlaceHolderStr() as string:
                                    content += string.text
                                case PlaceHolderFishItem() as fish:
                                    content += f"[ __{char_info.name}'s record of {ITEM_NAME_MAPPING.get(fish.fish_id, fish.fish_id)}__ ]"

                    case 8009005:  # share fishing record
                        header = f"{char_info.name} {"🌱" if char_info.is_newbie else ""} [{self.CHANNEL_MAPPING[channel_type]}]"
                        content = ""

                        for placeholder in hypertext.hypertext_contents:
                            placeholder_content = self._decode_placeholder(placeholder)
                            match placeholder_content:
                                case PlaceHolderStr() as string:
                                    content += string.text
                                case PlaceHolderFishPersonalTotal() as record:
                                    content += f"[ __{record.user_name}'s fishing profile__ ]"

                    case 5001012:  # Welcome guild message??
                        placeholder = hypertext.hypertext_contents[0]
                        player: PlaceHolderPlayer = self._decode_placeholder(placeholder)

                        header = "Guild Administrator"
                        content = f"Welcome __{player.name}__ to the Guild!"

        if header and content:
            logger.info(f"{header=} {content=}")
            webhook = SyncWebhook.from_url(self.webhook_url, session=self.session)
            webhook.send(content, username=header)
        else:
            logger.info(channel_type, message)


def main():
    import asyncio
    from discord.utils import setup_logging

    async def async_main():
        setup_logging()

        bot = BPSRRelayBot(command_prefix=".", intents=Intents.default())
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

    asyncio.run(async_main())


if __name__ == '__main__':
    main()
