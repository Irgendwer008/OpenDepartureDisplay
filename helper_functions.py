from typing import TYPE_CHECKING
# Only for typechecking to prevent a circular import but still be able to use the Window type setting
if TYPE_CHECKING:
    from gui import Window
from data_classes import Station, StopPoint, Departure
from log import logger

from datetime import datetime, timedelta
import pandas as pd
from urllib.request import urlretrieve
from urllib.error import HTTPError
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

def create_stations(stations_config: dict) -> list[Station]:
    """Create station objects from stations config

    Args:
        stations_config (dict): Dictionary with all stations config

    Returns:
        list[Station]: list of all station objects created from the config dictionary
    """    
    stations: dict[Station] = []
    
    # cycle through every entry in the stations config
    for station_name in stations_config:
        
        stop_points = []
        
        # cycle through every stop_point assigned to one station
        for stop_point in stations_config[station_name]["stops"]:
            # get stop_point_ref
            stop_point_ref = stop_point["stop_point_ref"]
            
            # get prefix and suffix, if the exist
            prefix = None
            suffix = None
            try:
                prefix = stop_point["prefix"]
            except KeyError:
                pass
            try:
                suffix = stop_point["suffix"]
            except KeyError:
                pass
            
            # append the stop point its station
            stop_points.append(StopPoint(
                stop_point_ref=stop_point_ref,
                prefix=prefix,
                suffix=suffix
            ))
            
            # print a debug notice, 
            if prefix is None: logger.debug(f"station {station_name} / {stop_point_ref} doesn't have a prefix configured")
            if suffix is None: logger.debug(f"station {station_name} / {stop_point_ref} doesn't have a suffix configured")
        
        lead_time_minutes = float(stations_config[station_name]["lead_time_minutes"])
        
        # add the new station with its newly creted stop point to the list of station objects
        stations.append(Station(
            name=station_name,
            lead_time_minutes=lead_time_minutes,
            stop_points=stop_points
        ))
    
    return stations

def get_all_used_stoppoints(windows: list["Window"]) -> list[StopPoint]:
    """Returns a list of all StopPoint objects that are used by any of the window's stations

    Args:
        windows (list[Windows]): List of windows, whose stations should be checked for stop points

    Returns:
        list[StopPoint]: list of all StopPoints used
    """    
    all_stop_points: list[StopPoint] = []
    
    for window in windows:
        for stop_point in window.station.stop_points:
            if stop_point not in all_stop_points:
                all_stop_points.append(stop_point)
    
    return all_stop_points
    
def download_line_color_list(filename: str) -> bool:
    """Downloads the latest line color codes for later use in icon creation and saves the file to the specified filename

    Args:
        filename (str): filename to save the file as

    Returns:
        bool: True, if the data could be downloaded successfully
    """    
    #TODO: change to use official kvv data
    #TODO: make argument instead of hardcoded url
    
    # try to donwload from url
    url = "https://raw.githubusercontent.com/Traewelling/line-colors/refs/heads/main/line-colors.csv"
    try:
        # downloads url content to the specified filename
        urlretrieve(url, filename)
        return True
    except HTTPError:
        logger.exception("Line color data could not be downloaded!y")
        return False

def get_line_color(line_name: str, filename: str, fallback_colors: tuple[str, str], SEV_lines_use_normal_line_icon_colors: bool) -> tuple[str, str]:
    """Returns a tuple of two strings containing color hex codes for background and text color for line icon creation. Sets ICs and ICEs to DB-red color and FLXs to FLX-green color.

    Args:
        line_name (str): Name of the Line
        filename (str): File location of the line color data
        fallback_colors (tuple[str, str]): colors to use if line is not to be found in the file
        SEV_lines_use_normal_line_icon_colors (bool): whether or not "SEV" lines should use their normal lines colors (see README -> general configuration)

    Returns:
        tuple[str, str]: tuple of (backgroundcolor, textcolor) in hex code
    """
    
    # Filter out preset colors for superregional train lines
    if line_name.startswith("ICE") or line_name.startswith("IC"):
        return ("#EC0016", "#FFFFFF")
    if line_name.startswith("FLX"):
        return ("#97d700", "#FFFFFF")
    
    # reads in the data and filters the lines for lines by kvv
    df = pd.read_csv(filename)
    filtered_df = df[df['shortOperatorName'].str.contains('kvv', case=False, na=False)]
    
    # find the line in the filtered data
    result = filtered_df[filtered_df["lineName"] == line_name]

    try:
        if result.empty: # If line could not be found
            if SEV_lines_use_normal_line_icon_colors and line_name[0:3] == "SEV": # Try to search for a SEV's normal line number, if configured to do so
                result = filtered_df[filtered_df["lineName"] == line_name[3:]]
                if result.empty:
                    raise IndexError("Line name not found")
            else: 
                raise IndexError("Line name not found")
        # if line can be found: 
        return result["backgroundColor"].array[0], result["textColor"].array[0]
    except IndexError:
        # return default colors if no line colors could be found
        return fallback_colors
    
def get_time_from_now(time: datetime, time_zone: str) -> timedelta:
    """Returns a timedalta of the time between now and "time"

    Args:
        time (datetime): The datetime to calculate the timedelta to
        time_zone (str): the applicable timezone

    Returns:
        timedelta: The time between now and the specified datetime
    """    
    return time - datetime.now().replace(tzinfo=ZoneInfo(time_zone))

def format_platform(platform: str) -> str:
    """Removes "Gleis", "Platform", "Bahnsteig" or similiar terms (characters before the first spae) before the platform number.

    Args:
        platform (str): The String to format

    Returns:
        str: Only the line number
    """
    # split string by spaces
    words = platform.split(" ")
    # If there are more that one the number is likely preceeded by "platform " or similar, which shall be removed. If not, just return the input string.
    if len(words) > 1:
        return " ".join(words[1:])
    else:
        return platform

def get_departures_from_xml(stop_point_ref: str,
                            tree: ET.ElementTree, 
                            all_stations: list[Station], 
                            fallback_line_icon_colors: tuple[str, str], 
                            SEV_lines_use_normal_line_icon_colors: bool) -> list["Departure"]:
    """Returns all the departures as Objects in the given xml response from the Trias API

    Returns:
        list[Departure]: A list of all the departures
    """
    tree_root = tree.getroot()

    # Define namespaces
    ns = {
        'tri': 'http://www.vdv.de/trias',
        'siri': 'http://www.siri.org.uk/siri'
    }

    departures: list[Departure] = []

    # find all StopEvents in the xml tree
    for event_result in tree_root.findall('.//tri:StopEventResult', ns):
        if event_result.find('.//tri:StopPointRef', ns).text.startswith(stop_point_ref):
            event = event_result.find('tri:StopEvent', ns)
            
            # Get departure times
            planned_time = datetime.fromisoformat(event.find('.//tri:ServiceDeparture/tri:TimetabledTime', ns).text)
            try:
                estimated_time = datetime.fromisoformat(event.find('.//tri:ServiceDeparture/tri:EstimatedTime', ns).text)
            except Exception:
                estimated_time = None

            # Get line name and destination
            published_line_name = event.find('.//tri:PublishedLineName/tri:Text', ns).text
            # TODO: make not hardcoded
            words = published_line_name.split(" ")
            if len(words) > 1 and words[1] == "SEV":
                line_number = "SEV" + "".join(words[-1])
            if len(words) > 0:
                if words[-1] == "InterCityExpress":
                    line_number = "ICE" + "".join(words[1:2])
                elif words[-1] == "InterCity":
                    line_number = "IC" + "".join(words[1:2])
                elif words[-1] == "Flixbus":
                    line_number = "FLX" + "".join(words[-1])
                else: 
                    line_number = words[-1]
            
            destination = event.find('.//tri:DestinationText/tri:Text', ns).text
            
            # platform
            try:
                platform = format_platform(event.find('.//tri:PlannedBay/tri:Text', ns).text)
            except AttributeError:
                platform = None
            
            # get stop_point
            for station in all_stations:
                for stop_point in station.stop_points:
                    if stop_point.stop_point_ref == stop_point_ref:
                        departure_station = station
                        departure_stop_point = stop_point
            
            # mode
            mode = event.find('.//tri:Mode/tri:PtMode', ns).text

            # Get colors from github table
            background_color, text_color = get_line_color(line_number, "line-colors.csv", fallback_line_icon_colors, SEV_lines_use_normal_line_icon_colors)

            # Create Departure
            departure = Departure(
                line_number=line_number,
                destination=destination,
                platform=platform,
                station=departure_station,
                stop_point=departure_stop_point,
                mode=mode,
                background_color=background_color,
                text_color=text_color,
                planned_time=planned_time,
                estimated_time=estimated_time
            )

            # Add departure to list
            departures.append(departure)

    return departures

def get_departures_for_window(window: "Window", all_departures: list[Departure]):
    """Returns all departures to be displayed by any one window

    Args:
        window (Window): Window to find the departures for
        all_departures (list[Departure]): A list of all departures

    Returns:
        list[Departure]: List of all the departures for this window
    """    
    window_departures: list[Departure] = []
    
    # go through all departures
    for departure in all_departures:
        # if it's station is the same as the window's station, add it to the list
        if departure.station == window.station:
            window_departures.append(departure)
            
    return window_departures
