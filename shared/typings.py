from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass
class Giveaway:
    # pylint: disable=too-many-instance-attributes
    _id: str
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    created: int
    publish_time: int
    button_text: str
    admin: int
    channels: list[int]
    send_to_id: int
    members: list[GiveawayMember]
    ip_counter: dict[str, int]
    status: Literal["start", "end", "waiting"]
    winners: list[GiveawayMember]
    winners_count: int
    msg_ids: list[int]
    deadline: TimeDeadline | MembersDeadline
    top_msg_id: int | None
    preview_text: str

@dataclass
class GiveawayMember:
    name: str
    id: int
    def __hash__(self):
        return self.id

@dataclass
class TimeDeadline:
    type: Literal["time"]
    time: int

@dataclass
class MembersDeadline:
    type: Literal["members"]
    members: int

@dataclass
class Channel:
    _id: int
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    channel_name: str
    admin: int
    link: str | None
