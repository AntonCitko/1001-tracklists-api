import requests
import re
from fake_headers import Headers
from bs4 import BeautifulSoup

SOURCES = {
    "1": "beatport",
    "2": "apple",
    "4": "traxsource",
    "10": "soundcloud",
    "13": "video",
    "36": "spotify",
}

class Tracklist:
    """An object representing a tracklist on 1001tracklists.com

    Keyword arguments:

    url -- The url of the tracklist page.

    Class variables:

    url

    title -- Title of the Tracklist
    
    tracks -- List of Track Objects

    Run tracklist_name.fetch() to get data.
    """
    
    def __init__(self, url=""):
        self.url = url
        if not url:
            with open("test.html") as f:
                self.soup = BeautifulSoup(f, "html.parser")
        else:
            self.url = url
        self.title = ""
        self.tracks = []
        self.soup = None

    def __repr__(self):
        url = f"<Tracklist> {self.url}\n"
        title = f"<Title> {self.title}\n"
        tracks = ""
        for track in self.tracks:
            tracks += f"    <Track> {track.title}\n"
        return url + title + tracks
    
    def get_soup(self, url):
        """"Retrtieve html and return a bs4-object."""
        response = requests.get(url, headers=Headers().generate())
        return BeautifulSoup(response.text, "html.parser")
    
    def fetch(self):
        """Fetch title and tracks from 1001.tl"""

        self.soup = self.get_soup(self.url)
        self.title = self.soup.title.text
        self.tracks = self.fetch_tracks()

    def fetch_tracks(self):
        """Fetches metadata, url, and external ids for all tracks.
        Result is saved as Track()-Objects to tracklist.tracks."""
        result = []

        # Find track containers.
        track_table = self.soup.find_all("tr", class_="tlpItem")

        for track in track_table:
            # Find all hyperlinks for each track container
            links = track.find_all("a")
            for link in links:
                # If track url found -> Save
                if "/track/" in link["href"]:
                    track_url = link["href"]
                    break;

            # Find span-elements with class="trackValue", which contain the track id.
            info = track.find_all("td")[2]
            track_id = info.find("span", class_="trackValue").get("id")[3:]

            # Generate a new Track object using gathered data.
            new = Track(
                url = "",#track_url,
                track_id = track_id,
                title = info.find("meta", itemprop="name").get("content")
            )

            # Get external ids for new track.
            new.fetch_external_ids()
            result.append(new)
        return result

    def get_tracks(self):
        for track in self.tracks:
            print(track)
        return self.tracks

class Track(Tracklist):
    """An object representing a track on 1001tracklists.com

    Keyword arguments:

    url -- The url of the tracklist page.

    track_id -- Internal 1001.tl-track id

    title -- Title

    external_ids -- List of available streaming ids

    Run track_name.fetch() to get data.

    """
    
    def __init__(self, url="", track_id=0, title="", external_ids={}):
       
        self.url = url
        self.track_id = track_id
        self.title = title
        self.external_ids = external_ids
        self.soup = None
        

    def __repr__(self):
        title = f"<Title> {self.title}\n"
        track_id = f"<ID> {self.track_id}\n"
        external = f"<External> {[x for x in self.external_ids]}\n"
        url = f"<URL> {self.url}...\n"
        return url + title + track_id + external

    def fetch(self):
        """Fetch title, track_id and external ids."""

        if not self.soup:
            self.soup = self.get_soup(self.url)
        
        self.title = self.soup.find("h1", id="pageTitle").text.strip()

        # Extract track id from <li title="add media links for this track">-element.
        track_id_source = self.soup.find("li", title="add media links for this track")
        try:
            # Extract content of "onclick" attribute, which is a js-function.
            track_id_source = track_id_source.get("onclick")
            # Extract track id (after idItem-parameter) using regex.
            self.track_id = re.search("(?<=idItem:\\s).[0-9]+", track_id_source).group(0)
        except AttributeError:
            print(track_id_source)

        # Fetch external ids
        self.fetch_external_ids()

    def get_external(self, *services):
        """Returns external ids of passed streaming services.

        Arguments:

        services -- One or more streaming service names.
                    * for all.

        Services:

        spotify, video, apple, traxsource, soundcloud, beatport
        """
        if services[0] == "*":
            return self.external_ids

        result = {}
        for service in services:
            try:
                result[service] = self.external_ids[service]
            except KeyError:
                print(f"ERROR: No id found for {service}")
        return result

    def fetch_external_ids(self):
        """Fetch external ids."""
        result = {}
        URL = f"https://www.1001tracklists.com/ajax/get_medialink.php?idObject=5&idItem={self.track_id}&viewSource=1"
        
        # Request all medialinks from 1001tl-API.
        response = requests.get(URL).json()

        # Add external ids to external_ids.
        if response["success"]:
            data = response["data"]
            for elem in data:
                try: 
                    result[SOURCES[elem["source"]]] = elem["playerId"]
                except KeyError:
                    print("Source: ", elem["source"], "not defined.")
            self.external_ids = result

        else: 
            print("Request failed:", response)