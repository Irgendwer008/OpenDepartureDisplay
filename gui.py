from datetime import datetime
from PIL import Image, ImageTk
import pyqrcode
import tkinter as tk

from config import Config
from data_classes import Station, Departure
from helper_functions import get_time_from_now
from gui_line_icons import LineIcons
from log import logger

class Window:
    """A class for every Window to be displayed
    """    
    @staticmethod
    def create_windows(config: Config,
                       all_stations: dict[Station],
                       icon_handler: LineIcons) -> list["Window"]:
        """Creates all Windows found in the specified config

        Returns:
            list[Window]: A list of all Windows created
        """        
        
        windows: list[Window] = []
        
        # go through all windows configured
        for window_config in config.windows:
            # go through all stations to find the one assigned to this window
            for station in all_stations:
                if station.name == window_config["station"]:
                    break
            # create the window object and add it to the list
            windows.append(Window(window_config, station, icon_handler, config))
        
        return windows

    def __init__(self, window_config: dict, station: Station, icon_handler: LineIcons, config: Config, number_of_departure_entries: int = 10):
        """Creates a Window by setting variables, creating the windows widgets and filling it with (emtpy) departure entries

        Args:
            window_config (dict): The window's config dict
            station (Station): The station object assigned to this window
            icon_handler (LineIcons): The Icon handler that creates and caches the icons
            config (Config): the whole config object
            number_of_departure_entries (int, optional): Number of entries to fit onto this screen. Defaults to 10.
        """      
        
        # set some instance wide variables from the parameters  
        self.station = station
        self.icon_handler = icon_handler
        self.config = config
        self.number_of_departure_entries=number_of_departure_entries
        
        def close(_ = None):
            logger.critical("Ctrl+q or Ctrl+c pressed by user, exiting program now")
            quit()
        
        # Create a new tkinter window
        window = tk.Toplevel()
        self.window = window
        window.overrideredirect(True) 
        window.geometry(f"{window_config['width']}x{window_config['height']}+{window_config['position_x']}+{window_config['position_y']}")
        #window.attributes("-fullscreen", True)
        # remove window header bar to make it appear fullscreen
        window.attributes('-type', 'splash')
        # add function to quit at any time by pressing Ctrl + q or Ctrl + c
        window.bind("<Control-q>", close)
        window.bind("<Control-c>", close)
        
        # set this windows height and width
        self.height = window_config["height"]
        self.width = window_config["width"]
        
        # calculate and create header
        header_height = int(self.height / 12)
        departure_frame_height = self.height - header_height
        self.DepartureEntry_height = int(((departure_frame_height) / (number_of_departure_entries * 2 + 1)) * 2) # +1 for departure entry header (column description)
        self.padding_size = int(self.height / 75)
        self.header_font = ("liberation sans", int(self.height / 25))
        self.DepartureEntry_font = ("liberation sans", int(self.height / 25))

        # create variable for station name to be displayed in the header
        self.stationname = tk.StringVar(value=self.station.name)
        
        # list of all icons used by a window
        #TODO: make this use general configs; not hardcoded
        self.icons = {
            "stop": ImageTk.PhotoImage(Image.open("images/stop_icon.png").resize((int(header_height - 2 * self.padding_size), int(header_height - 2 * self.padding_size)))),
        }

        # create header frame
        self.headerframe = tk.Frame(window, background=self.config.colors["header_background"])
        self.headerframe.place(anchor="nw", x=0, y=0, height=header_height, width=self.width)

        # create the icon in the top left
        self.stopiconlabel = tk.Label(self.headerframe, image=self.icons["stop"], bg=self.config.colors["header_background"])
        self.stopiconlabel.pack(side="left", padx=self.padding_size, pady=self.padding_size)
        
        # create the station label
        self.stationlabel = tk.Label(self.headerframe, textvariable=self.stationname, font=self.header_font, anchor="w", justify="left", fg=self.config.colors["header_text"], bg=self.config.colors["header_background"])
        self.stationlabel.pack(side="left", padx=self.padding_size)

        # create the clock in the top right
        self.timelabel = tk.Label(self.headerframe, text="", font=self.header_font, anchor="w", justify="right", fg=self.config.colors["header_text"], bg=self.config.colors["header_background"])
        self.timelabel.pack(side="right", padx=self.padding_size)
        
        # calculate and refresg time every second
        def time():
            self.timelabel.after(1000, time)
            string = datetime.now().strftime('%H:%M:%S')
            self.timelabel.config(text=string)
        time()
        
        # add a QR-Code to the header (if configred in settings)
        if self.config.general["QR-Code-content"] is not None and self.config.general["QR-Code-height"] > 0:
            self.qr_code = QRCodeLabel(self.headerframe, int(header_height * self.config.general["QR-Code-height"]), self.config.general["QR-Code-content"], self.config.colors["qr_code_background"], self.config.colors["qr_code_foregreound"])
            self.qr_code.configure(height=header_height, width=header_height, background=self.config.colors["header_background"])
            self.qr_code.pack(side="right")
            self.qr_code.pack_propagate(0)
        
        # create the frame for the departures to be shown
        self.departuresframe = tk.Frame(window)
        self.departuresframe.place(x=0, y=header_height, height=self.height-header_height, width=self.width)

        self.departure_entries: list[DepartureEntry] = []
        
        # create the departures entry header for column description
        self.departure_entries.append(DepartureEntry_Header(self))
        
        # fill the rest with blank departure entries
        for i in range(number_of_departure_entries):
            self.departure_entries.append(DepartureEntry(self))
        
    def refresh(self, departures: list[Departure] | None):
        """Refreshes the information of this window with the new specified departures

        Args:
            departures (list[Departure] | None): List of Departures to populate this window with
        """        
        
        # sort all departures by their estimated time if available. if not, fall back to their planned time
        departures.sort(key=lambda x: (x.estimated_time if x.estimated_time is not None else x.planned_time))
        
        #TODO: handle no departures
        if len(departures) < 1 or departures is None:
            return
        
        for i in range(len(departures)):
            self.departure_entries[i + 1].update(departures[i], self.icon_handler, i)
            if i + 1 >= self.number_of_departure_entries:
                # stop in case there are more departures than can be shown in this window
                break
    
        # Add departures below the departure entry header
        for DepartureEntry in self.departure_entries[i + 2:]:
            DepartureEntry.clear(i)

class DepartureEntry:
    """A class for a single departure entry to be displayed within windows
    """    
    def __init__(self, window: Window):
        """Create a DepartureEntry to be displayed within windows

        Args:
            window (Window): The window in which this departure is to be displayed
        """
        
        # Create some instance wide variables from arguments
        self.window = window
        self.height = window.DepartureEntry_height
        self.padding = int(self.height / 8)
        self.font = window.DepartureEntry_font
        background = self.window.config.colors["departure_entry_lighter"]
        text_color = self.window.config.colors["departure_entry_text"]
        
        # Create tkVars
        self.destination_var = tk.StringVar()
        self.platform_var = tk.StringVar()
        self.time_text_var = tk.StringVar()

        # Create the departure entry frame and its content
        self.frame = tk.Frame(window.departuresframe, bg=background, height=self.height)
        self.frame.pack(side="top", fill="x", ipadx=self.padding*2)
        self.frame.pack_propagate(0)

        self.destination_label = tk.Label(self.frame, textvariable=self.destination_var, fg=text_color, bg=background, font=self.font)
        self.destination_label.place(anchor="w", x=2*self.height, rely=0.5, relheight=0.8)
        
        self.platform_label = tk.Label(self.frame, textvariable=self.platform_var, fg=text_color, bg=background, font=self.font)
        self.platform_label.place(anchor="center", relx=0.8, rely=0.5, relheight=0.8)

        self.time_label = tk.Label(self.frame, textvariable=self.time_text_var, fg=text_color, bg=background, font=self.font)
        self.time_label.place(anchor="e", x=window.width-self.padding, rely=0.5, relheight=0.8)
        
        self.line_icon_label = tk.Label(self.frame, bg=background)
        self.line_icon_label.place(anchor="center", x=self.height, rely=0.5)
    
    def update(self, departure: Departure, icon_handler: LineIcons, index: int):
        """Update a departure entry frame / its contents. Creating new ones takes waay to long and is also kinda ugly. This method instead allows quietly updating values without taking too long and wihtout disrutping the user experience

        Args:
            departure (Departure): Object to the departure to update
            icon_handler (LineIcons): The Icon handler which creates and caches line icons
            index (int): Index of this departure in the list. Used for alternating background of entries
        """        
        
        # Alternate Background of departure entries
        if index % 2:
            background = self.window.config.colors["departure_entry_darker"]
        else:
            background = self.window.config.colors["departure_entry_lighter"]
            
        # Set new background to all the widgets
        self.frame.configure(background=background)
        self.destination_label.configure(background=background)
        self.platform_label.configure(background=background)
        self.time_label.configure(background=background)

        # Choose estimated time if one is available, otherwise use planned time
        if departure.estimated_time is None:
            time_shown = departure.planned_time
        else:
            time_shown = departure.estimated_time
        
        # get total seconds from now until departure
        seconds = get_time_from_now(time_shown, self.window.config.general["time_zone"]).total_seconds()

        # Format the time string based on remaining seconds
        if seconds < 60:
            time_str = "Jetzt"
        elif seconds < 3600:
            time_str = f"{int(seconds // 60)} min"
        else:
            time_str = f"{int(seconds // 3600)} h {int((seconds % 3600) // 60)} min"

        # Scalar for general size appearance of icon size
        icon_scale = 0.8

        # Preprocess line number
        text = departure.line_number
        if text == "InterCityExpress": text = "ICE"
        if text == "InterCity": text = "IC"
        # Some black magic to make nice icon dimension while being adaptive to line number length
        icon_width = int(icon_scale * (self.height * (text.__len__()*0.4) + 2.5 * self.padding))
        icon_height = int(icon_scale * (self.height - 2* self.padding))
        
        # Create the icon (-> gui_line_icons.py)
        self.line_icon_label.configure(image=icon_handler.get_icon(departure.mode, icon_width, icon_height, int((icon_height) / 4), text, departure.background_color, departure.text_color, self.font), background=background)

        # Platform formatting stuff
        #prefix = departure.stop_point.prefix if departure.stop_point.prefix is not None else ""
        #suffix = departure.stop_point.suffix if departure.stop_point.suffix is not None else ""
        #platform_text = (prefix + " " + departure.platform + " " + suffix) if departure.platform is not None else (prefix + " N/A " + suffix)
        #
        # Apparently things got changed so that the suffix is also contained in the platform string, therefor:
        platform_text = departure.platform if departure.platform is not None else "N/A"
        
        
        # Update tkVars
        self.destination_var.set(departure.destination)
        self.platform_var.set(platform_text)
        self.time_text_var.set(time_str)
        
    def clear(self, index: int):
        """Clear this entry if no departure was found to fill it

        Args:
            index (int): Index of last filled departure entry for a non-alternating background in all the empty departure entries at the end
        """        
        self.line_icon_label.destroy()
        self.destination_var.set("")
        self.platform_var.set("")
        self.time_text_var.set("")
        
        # Apply background color
        if index % 2:
            self.frame.configure(background=self.window.config.colors["DepartureEntry_darker"])
        else:
            self.frame.configure(background=self.window.config.colors["DepartureEntry_lighter"])
        
class DepartureEntry_Header(DepartureEntry):
    """A classs for the first DepartureEntry which acts as column description of the following departure entries
    """
    def __init__(self, window: Window):
        """Cretes the first DepartureEntry which acts as column description of the following departure entries

        Args:
            window (Window): The window the departures will be displayed in
        """
        # Use a smaller text size to use up less space
        header_font = (window.DepartureEntry_font[0], int(window.DepartureEntry_font[1] / 2))
        
        # Reduce height and padding to leave mor space for departures
        height = window.DepartureEntry_height / 2
        padding = int(height / 8)
        
        # Set background color
        background = window.config.colors["departure_entry_darker"]
        text_color = window.config.colors["departure_entry_text"]

        # Create the departure entry frame and its content
        frame = tk.Frame(window.departuresframe, bg=background, height=height)
        frame.pack(side="top", fill="x", ipadx=padding*2)
        frame.pack_propagate(0)

        line_icon = tk.Label(frame, text="Linie", fg=text_color, bg=background, font=header_font)
        line_icon.place(anchor="center", x=2 * height, rely=0.5)

        destination_label = tk.Label(frame, text="Richtung", fg=text_color, bg=background, font=header_font)
        destination_label.place(anchor="w", x=4*height, rely=0.5, relheight=0.8)

        platform_label = tk.Label(frame, text="Gleis / Bstg.", fg=text_color, bg=background, font=header_font)
        platform_label.place(anchor="center", relx=0.8, rely=0.5, relheight=0.8)

        time_label = tk.Label(frame, text="Ankunft", fg=text_color, bg=background, font=header_font)
        time_label.place(anchor="e", x=window.width-padding, rely=0.5, relheight=0.8)

# The method for creating the QR-Code was used fromm this stackoverflow thread:
# https://stackoverflow.com/questions/57128265/qrcode-displaying-in-tkinter-gui-python   
class QRCodeLabel(tk.Label):
    """This Class creates a Tk Label that specificaly contains a QR-Code for the window header
    """    
    def __init__(self, parent, size: int, qr_data, background: str, foreground: str):
        """Creates a Tk Label that specificaly contains a QR-Code for the window header

        Args:
            parent (_type_): Parent Tk widget
            size (int): size fo the QR-code in pixels
            qr_data (_type_): Content to be encoded in the QR-Code
            background (str): QR-Code Backround color hex code
            foreground (str): QR-Code Foreground color hex code
        """        
        
        # Init super Tk Label
        super().__init__(parent)
        
        # Create a QR-Code image
        qrcode = pyqrcode.create(qr_data)
        tmp_png_file = "images/QRCode.png"        
        qrcode.png(tmp_png_file, scale=1, quiet_zone=2, background=(int(background[1:3], 16), int(background[3:5], 16), int(background[5:7], 16), 255), module_color=(int(foreground[1:2], 16), int(foreground[3:4], 16), int(foreground[4:5], 16), 255))
        
        # Open and Resize the Image
        self.original = Image.open(tmp_png_file)
        resized = self.original.resize((size, size))
        
        # Convert it to a PhotoImage
        self.image = ImageTk.PhotoImage(resized)
        
        # Apply it to the Tk Label
        self.configure(image=self.image)