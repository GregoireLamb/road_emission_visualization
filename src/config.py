import yaml

class Config:
    def __init__(self):
        with open("../config.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            self.MAPS_API_KEY = self.config["MAPS_API_KEY"]
            self.RESULTS_PATH = self.config["RESULTS_PATH"]
            self.DATA_PATH = self.config["DATA_PATH"]
