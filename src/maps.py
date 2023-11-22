import googlemaps
from datetime import datetime, timedelta
import polyline
import pandas as pd

class Maps:
    def __init__(self, api_key):
        self.API_KEY = api_key
        if self.API_KEY != "YOUR_API_KEY":
            self.gmaps = googlemaps.Client(key=self.API_KEY)
            print("Google Maps API key loaded")
        else:
            print("Please enter your Google Maps API key in config.yaml")

    def get_directions(self, origin, destination, departure_time=datetime.now(), mode="driving", save=False):
        """
        Get arrival time from origin to destination
        :param origin: as Place_id
        :param destination: as Place_id
        :param departure_time: as datetime
        :param mode: One of "driving", "walking", "bicycling" or "transit"
        :return: arrival_date, delay
        """
        decoded_polyline, directions_result= "", ""
        distance = 0
        try:
            directions_result = self.gmaps.directions(origin,
                                                      destination,
                                                      mode=mode,
                                                      departure_time=departure_time)
            distance, encoded_polyline, northeast, southwest = self.parse_destinations(directions_result, save=save)
            decoded_polyline = polyline.decode(encoded_polyline)
        except:
            print("No route found for origin: {} and destination: {}".format(origin, destination))

        return distance, decoded_polyline, northeast, southwest

    def parse_destinations(self, directions_result, save=True):
        """
        Parse destinations
        :param directions_result:
        :return: arrival time in string format
        """
        distance = directions_result[0]["legs"][0]["distance"]["value"]
        encoded_polyline = directions_result[0]["overview_polyline"]["points"]
        northeast = directions_result[0]["bounds"]["northeast"]
        southwest = directions_result[0]["bounds"]["southwest"]

        # if save add distance and encoded_polyline to csv
        if save:
            with open("../data/response.csv", "a") as f:
                f.write(str(distance)+";")
                f.write(str(northeast)+";")
                f.write(str(southwest)+";")
                f.write(str(encoded_polyline)+"\n")

        return distance, encoded_polyline, northeast, southwest