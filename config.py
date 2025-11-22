from log import logger
import re
import yaml
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class Config:
    def __init__(self, file_list: list[str] = ["config.yaml", "config.yml"]):
        """Create a new, complete config object from a config file. The selected file is the first of the list that can be found in the current directory.

        Args:
            file_list (list[str], optional): List of filename-strings to search for to import as a config file. Defaults to ["config.yaml", "config.yml"].

        Raises:
            FileNotFoundError: If no file with any of the names in the list can be found.
            Exception: If any other error ocurrs while searching / reading the file as yaml config object.
        """        
        
        # Import config
        try:
            # try all file names from the list and (only) raise FileNotFoundError if none can befound
            success = False
            last_exception: Exception = None
            for file in file_list:
                try:
                    with open(file, "r") as file:
                        config = yaml.safe_load(file)
                    success = True
                    break
                except FileNotFoundError as e:
                    last_exception = e
            if not success:
                raise last_exception
        except FileNotFoundError:
            logger.critical('FileNotFoundError while opening file "config.yaml", does it exist? Quitting program.')
            quit()
        except Exception:
            logger.critical("Error while opening configuration file, quitting program!", exc_info=True)
            quit()
        
        # If that was successful, set config dict...
        self.config = config
        
        # ...and then get and fill all the sections
        self._check_and_get_general()
        self._check_and_get_windows()
        self._check_and_get_stations()
        self._check_and_get_credentials()
        self._check_and_get_colors()
    
    def _check_and_get_general(self):
        """Checks if the general config section was typed correctly and, if true, saves it to the config object

        Raises:
            KeyError: If a neccessary key (config setting) cannot be found in the config section
            ValueError: If any setting does not have the value format expected
            ZoneInfoNotFoundError: If the specified string for time zone is not a valid time zone
        """        
        try:
            # check if general section exists
            self.general: dict = self.config["general"]
            
            # check if time zone setting exists
            setting = "time_zone"
            Helper.is_valid_ZoneInfo(self.general[setting])
            
            # check if SEV lines coloring setting exists and is either true or false
            setting = "SEV-lines use normal line icon colors"
            Helper.is_true_false_caseinsensitive(self.general[setting])
            
            # check if QR code content exists
            setting = "QR-Code-content"
            Helper.does_exist(self.general, setting)
            
            # if qr-code content is not empty: check if QR code height exists and is a float between including 1 and 0
            if self.general["QR-Code-content"] not in [None, "None", "none"]:
                setting = "QR-Code-height"
                Helper.is_float(self.general[setting])
                if not Helper.is_in_range(self.general[setting], (0, 1)):
                    raise ValueError
            else:
                self.general["QR-Code-content"] = None
            
        except KeyError:
            logger.critical(f'KeyError while reading general setting "{setting}", have you typed it correctly? Quitting program.', exc_info=True)
            quit()
        except ValueError:
            logger.critical(f'ValueError while reading general setting "{setting}", it is not a valid value for this setting! Quitting program.', exc_info=True)
            quit()
        except ZoneInfoNotFoundError:
            logger.critical(f'ZoneInfoNotFoundError while reading general setting "{setting}", it is not a valid time sone identifier! See more in the README about this setting. Quitting program.', exc_info=True)
            quit()
    
    def _check_and_get_windows(self) -> list:
        """Checks if the windows section was typed correctly and, if true, saves it to the config object

        Raises:
            KeyError: If a neccessary key (windows setting) cannot be found in the windows section
            ValueError: If any setting does not have the value format expected
        """        
        # check if windows where configured correctly
        try:
            index = None
            # check if windows section exists
            self.windows: list = self.config["windows"]
            for try_window in self.windows:
                index = self.windows.index(try_window)
                # check if all the fields exist and are of correct type
                Helper.is_int(try_window["position_x"])
                Helper.is_int(try_window["position_y"])
                Helper.is_int(try_window["width"])
                Helper.is_int(try_window["height"])
                expected_station = try_window["station"]
                try:
                    self.config["stations"][expected_station] # also check if the wanted station actually exist in the stations config
                except KeyError:
                    logger.critical(f'KeyError while reading windows configuration, mentioned station {expected_station} does not exist in the station config part! Make sure you haven\'t mistyped it ore the stations config! Quitting program.', exc_info=True)
                    quit()
        except KeyError:
            if index is None:
                logger.critical('KeyError while reading windows configuration, have you typed "windows" correctly? Quitting program.', exc_info=True)
            else:
                logger.critical(f'KeyError while reading window #{index}\'s configuration, have you typed "position_x", "position_y", "width", "height" and "station" correctly? Quitting program.', exc_info=True)
            quit()
        except ValueError:
            logger.critical(f'ValueError while reading window #{index}\'s configuration, are "position_x", "position_y", "width" and "height" integers? Quitting program.', exc_info=True)
            quit()
    
    def _check_and_get_stations(self) -> dict:
        """Checks if the stations section was typed correctly and, if true, saves it to the stations object

        Raises:
            KeyError: If a neccessary key (station setting) cannot be found in the stations section
            ValueError: If any setting does not have the value format expected
        """     
        # check if stations where configured correctly
        try:
            try_station = None
            # check if stations section exists
            self.stations: dict = self.config["stations"]
            for try_station_key in self.stations.keys():
                # try each station in the list for its properties
                try_station: dict = self.stations[try_station_key]
                Helper.is_float(try_station["lead_time_minutes"])
                for stop in try_station["stops"]:
                    # check each stop_point of each station for its properties
                    Helper.does_exist(stop, "stop_point_ref")
                    # check if any mentioned properties are in this list to prevent accidental mistyping of an optional argument
                    for try_optional_argument in stop.keys():
                        if try_optional_argument not in ["stop_point_ref", "prefix", "suffix"]:
                            raise ValueError
        except KeyError:
            if try_station is None:
                logger.critical('KeyError while reading station configuration, have you typed "station" correctly? Quitting program.', exc_info=True)
            else:
                logger.critical(f'KeyError while reading station {try_station_key}\'s configuration, have you typed "stop_point_ref", "prefix", "suffix" and "lead_time_minutes" correctly? Quitting program.', exc_info=True)
            quit()
        except ValueError:
            logger.critical(f'ValueError while reading station {try_station_key}\'s configuration, invalid property "{try_optional_argument}"! Quitting program.', exc_info=True)
            quit()
    
    def _check_and_get_colors(self) -> dict:
        """Checks if the colors section was typed correctly and, if true, saves it to the colors object

        Raises:
            KeyError: If a neccessary key (color setting) cannot be found in the colors section
            ValueError: If any setting is not a valid hex color code string
        """     
        # check if configured colors are valid
        try:
            color = None
            self.colors: dict = self.config["colors"]
            for color in ["header_background",
                          "header_text",
                          "departure_entry_lighter",
                          "departure_entry_darker",
                          "departure_entry_text",
                          "default_icon_background",
                          "default_icon_text",
                          "qr_code_background",
                          "qr_code_foregreound"]:
                # check each color setting if it is a valid hex color code
                if not Helper.is_color_valid(self.colors[color]):
                    raise ValueError
            
        except KeyError:
            if color is None:
                logger.critical('KeyError while reading color configuration, have you typed "colors" correctly? Quitting program.', exc_info=True)
            else:
                logger.critical(f'KeyError while reading color {color}\'s configuration, have you typed it correctly? Quitting program.', exc_info=True)
            quit()
        except ValueError:
            logger.critical(f'ValueError while reading color {color}\'s configuration, it is not a valid hex code color! Quitting program.', exc_info=True)
            quit()
    
    def _check_and_get_credentials(self) -> dict:
        """Checks if the credentials section was typed correctly and, if true, saves it to the credentials object

        Raises:
            KeyError: If a neccessary key (credential setting) cannot be found in the credentials section
            ValueError: If any setting is not a valid credential string
        """     
        # check if credentials section exists
        try:
            self.credentials: dict = self.config["credentials"]
        except KeyError:
            logger.critical(f'KeyError while reading credentials config section, have you typed "credentials" correctly? Quitting program.', exc_info=True)
            quit()
        
        # check if url exists
        try:
            Helper.does_exist(self.credentials, "url")
        except KeyError:
            logger.critical(f'KeyError while reading credentials config section, have you typed "url" correctly? Quitting program.', exc_info=True)
            quit()
            
        # check if requestor_ref exists and is prosumeably correct (has same length as a known good one)
        try:
            if self.credentials["requestor_ref"].__len__() != 12:
                raise ValueError
        except KeyError:
            logger.critical(f'KeyError while reading credentials config section, have you typed "requestor_ref" correctly? Quitting program.', exc_info=True)
            quit()
        except ValueError:
            logger.warning(f'The requestor_ref given by the config has an unusual length, are you shure it is correct?')


class Helper:
    hex_color_regex = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    
    @staticmethod
    def does_exist(dict: dict, key) -> None:
        """tf do u think it does lol

        Args:
            dict (dict): dictionary
            key (_type_): key to check if in dictionary
        """        
        dict[key]
        
    @staticmethod
    def is_int(string: str) -> None:
        """Checks, if string is castable to an integer

        Args:
            string (str): String to check
            
        Raises:
            ValueError: Raised, if string is not castable to an intager
        """        
        int(string)
        
    @staticmethod
    def is_float(string: str) -> None:
        """Checks, if string is castable to a float

        Args:
            string (str): String to check
            
        Raises:
            ValueError: Raised, if string is not castable to a float
        """  
        float(string)
    
    @staticmethod
    def is_valid_ZoneInfo(string: str) -> bool:
        """Checks, if string denotes a valid time zone (e.g. "Europe/Berlin")

        Args:
            string (str): String to check
            
        Raises:
            ValueError: Raised, if string is not a valid time zone
        """  
        return ZoneInfo(string)
    
    @staticmethod
    def is_color_valid(color_string: str) -> bool:
        """Checks, if string is a valid (three byte) color code

        Args:
            color_string (str): String to check

        Returns:
            bool: True, if string is a hex color code
        """        
        regexp = re.compile(Helper.hex_color_regex)
        if regexp.search(color_string):
            return True
        return False
        
    @staticmethod
    def is_in_range(x: float, range: tuple[float, float] | tuple[None, float] | tuple[float, None]) -> bool:
        """Checks, if string denotes a valid time zone (e.g. "Europe/Berlin")

        Args:
            string (str): String to check
            
        Raises:
            ValueError: Raised, if string is not a valid time zone
        """  
        if range[0] is None:
            return x <= range[1]
        elif range[1] is None:
            return x >= range[0]
        else:
            return x <= max(range) and x >= min(range)
    
    @staticmethod
    def is_true_false_caseinsensitive(string: str, valid_values: list[str] = ['true', 'false']) -> None:
        """Checks, if string spells either "true" or "false"; regardless of case

        Args:
            string (str): String to check
            
        Raises:
            ValueError: Raised, if string is not true or false
        """  
        if str(string).lower() not in valid_values:
            raise ValueError

if __name__ == "__main__":
    print(Config().config)