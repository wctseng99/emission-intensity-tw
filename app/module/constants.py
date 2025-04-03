from typing import Dict, TypedDict


class LocationMapping(TypedDict):
    from_: str
    to: str


UNIT_NAME_TO_LOCATION: Dict[str, LocationMapping] = {
    "北送中潮流": {"from_": "北部", "to": "中部"},
    "東送中潮流": {"from_": "東部", "to": "中部"},
    "南送中潮流": {"from_": "南部", "to": "中部"},
    "北送東潮流": {"from_": "北部", "to": "東部"},
    "中送東潮流": {"from_": "中部", "to": "東部"},
    "南送東潮流": {"from_": "南部", "to": "東部"},
    "北送南潮流": {"from_": "北部", "to": "南部"},
    "中送南潮流": {"from_": "中部", "to": "南部"},
    "東送南潮流": {"from_": "東部", "to": "南部"},
    "中送北潮流": {"from_": "中部", "to": "北部"},
    "東送北潮流": {"from_": "東部", "to": "北部"},
    "南送北潮流": {"from_": "南部", "to": "北部"},
}

EXCLUDED_REGIONS = {"離島"}
