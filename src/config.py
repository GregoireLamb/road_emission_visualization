import yaml

class Config:
    def __init__(self):
        with open("../config.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            self.MAPS_API_KEY = self.config["MAPS_API_KEY"]
            self.DATA_PATH = self.config["DATA_PATH"]
