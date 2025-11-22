from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from log import logger
    
@dataclass
class StopPoint:
    """Class for one single StopPoint
    """    
    stop_point_ref: str
    prefix: str | None
    suffix: str | None
    
@dataclass
class Station:
    """Class for one Station with one or more StopPoints
    """
    name: str
    lead_time_minutes: float
    stop_points: list[StopPoint]

@dataclass
class Departure:
    """Class for a Departure and all its for display necessary information
    """    
    line_number: str
    destination: str
    platform: str
    station: Station
    stop_point: StopPoint
    mode: Literal["all", "unknown", "air", "bus", "trolleyBus", "tram", "coach", "rail", "intercityRail", "urbanRail", "metro", "water", "cable-way", "funicular", "taxi"]
    background_color: str
    text_color: str
    planned_time: datetime
    estimated_time: datetime | None = None