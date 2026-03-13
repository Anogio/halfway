from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedAgency:
    agency_id: str
    agency_name: str
    agency_url: str
    agency_timezone: str


@dataclass(frozen=True)
class NormalizedStop:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    location_type: str = "0"
    parent_station: str = ""


@dataclass(frozen=True)
class NormalizedRoute:
    route_id: str
    agency_id: str
    route_short_name: str
    route_long_name: str
    route_type: str


@dataclass(frozen=True)
class NormalizedTrip:
    route_id: str
    service_id: str
    trip_id: str
    direction_id: str = "0"


@dataclass(frozen=True)
class NormalizedStopTime:
    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int


@dataclass(frozen=True)
class NormalizedCalendar:
    service_id: str
    monday: int
    tuesday: int
    wednesday: int
    thursday: int
    friday: int
    saturday: int
    sunday: int
    start_date: str
    end_date: str


@dataclass(frozen=True)
class NormalizedCalendarDate:
    service_id: str
    date: str
    exception_type: int


@dataclass(frozen=True)
class NormalizedTransfer:
    from_stop_id: str
    to_stop_id: str
    transfer_type: int = 0
    min_transfer_time: int = 0


@dataclass(frozen=True)
class NormalizedPathway:
    pathway_id: str
    from_stop_id: str
    to_stop_id: str
    pathway_mode: int = 1
    is_bidirectional: int = 0
    length: float = 0.0
    traversal_time: int = 0


@dataclass(frozen=True)
class NormalizedFeedInfo:
    feed_publisher_name: str
    feed_publisher_url: str
    feed_lang: str
    feed_start_date: str
    feed_end_date: str
    feed_version: str


@dataclass
class NormalizedDataset:
    agencies: list[NormalizedAgency] = field(default_factory=list)
    stops: list[NormalizedStop] = field(default_factory=list)
    routes: list[NormalizedRoute] = field(default_factory=list)
    trips: list[NormalizedTrip] = field(default_factory=list)
    stop_times: list[NormalizedStopTime] = field(default_factory=list)
    calendars: list[NormalizedCalendar] = field(default_factory=list)
    calendar_dates: list[NormalizedCalendarDate] = field(default_factory=list)
    transfers: list[NormalizedTransfer] = field(default_factory=list)
    pathways: list[NormalizedPathway] = field(default_factory=list)
    feed_info: list[NormalizedFeedInfo] = field(default_factory=list)
