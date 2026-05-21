from enum import Enum

from google.protobuf.message import Message

from star_resonance_tracer.proto.enum_place_holder_type_pb2 import PlaceHolderType
from star_resonance_tracer.proto.stru_place_holder_buff_pb2 import PlaceHolderBuff
from star_resonance_tracer.proto.stru_place_holder_fish_item_pb2 import PlaceHolderFishItem
from star_resonance_tracer.proto.stru_place_holder_fish_personal_total_pb2 import PlaceHolderFishPersonalTotal
from star_resonance_tracer.proto.stru_place_holder_fish_rank_pb2 import PlaceHolderFishRank
from star_resonance_tracer.proto.stru_place_holder_item_pb2 import PlaceHolderItem
from star_resonance_tracer.proto.stru_place_holder_master_mode_pb2 import PlaceHolderMasterMode
from star_resonance_tracer.proto.stru_place_holder_pb2 import PlaceHolder
from star_resonance_tracer.proto.stru_place_holder_player_pb2 import PlaceHolderPlayer
from star_resonance_tracer.proto.stru_place_holder_scene_position_pb2 import PlaceHolderScenePosition
from star_resonance_tracer.proto.stru_place_holder_str_pb2 import PlaceHolderStr
from star_resonance_tracer.proto.stru_place_holder_timestamp_pb2 import PlaceHolderTimestamp
from star_resonance_tracer.proto.stru_place_holder_union_pb2 import PlaceHolderUnion
from star_resonance_tracer.proto.stru_place_holder_val_pb2 import PlaceHolderVal

__all__ = (
    "HypertextVariant",
    "decode_placeholder",
)

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

type SupportedPlaceholders = (
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
        | PlaceHolderScenePosition
)


class HypertextVariant(Enum):
    ITEM_SHARING = 3000001
    MASTER_SEAL = 1050001
    PERSONAL_SPACE = 3001001
    FISH = 8009003
    FISHING_RECORD = 8009005
    GUILD_WELCOME_NEW_MEMBER = 5001012
    GUILD_HUNT_PROGRESS = 5010003
    EE_CHAN = 1005003


def decode_placeholder(placeholder: PlaceHolder) -> SupportedPlaceholders:
    decoder = PLACEHOLDER_MAPPING.get(placeholder.type)
    if decoder is None:
        raise NotImplementedError

    # All compiled protobuf messages support ``FromString``
    return decoder.FromString(placeholder.bytes_content)  # type: ignore[attr-defined]
