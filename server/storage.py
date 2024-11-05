from models.data import Data, Folder
from models.config import Configuration, TrackingFolder
from utils.data_connector import DataConnector

default_config = Configuration(
    folders={
        "Example": TrackingFolder(
            name="Example",
            base_path="D:\\Example"
        )
    }
)

default_data = Data(
    folders={
        "Example": Folder(
            name="Example",
            base_path="D:\\Example",
            files={}
        )
    }
)

config_dc: DataConnector[Configuration] = DataConnector(relative_file_path='server/config.json', cls=Configuration, default_data=default_config)
data_dc: DataConnector[Data] = DataConnector(relative_file_path='server/data.json', cls=Data, default_data=default_data)

def get_config_dc() -> DataConnector[Configuration]:
    return config_dc

def get_data_dc() -> DataConnector[Data]:
    return data_dc