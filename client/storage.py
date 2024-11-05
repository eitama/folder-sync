from models.data import Data
from models.config import Configuration
from utils.data_connector import DataConnector

config_dc: DataConnector[Configuration] = DataConnector(relative_file_path='client/config.json', cls=Configuration)
data_dc: DataConnector[Data] = DataConnector(relative_file_path='client/data.json', cls=Data)

def get_config_dc() -> DataConnector[Configuration]:
    return config_dc

def get_data_dc() -> DataConnector[Data]:
    return data_dc