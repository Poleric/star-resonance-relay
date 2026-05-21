import polars as pl

__all__ = (
    "ITEM_NAME_MAPPING",
    "get_item_name"
)

ITEM_NAME_MAPPING = pl.read_json("./ref/StarResonanceData/ztable/ItemTable.json").transpose().unnest()


def get_item_name(item_config_id: int) -> str | None:
    try:
        return ITEM_NAME_MAPPING.filter(pl.col.Id == item_config_id).select("Name").item()
    except ValueError:
        return None