from box.exceptions import BoxValueError
import yaml
from box import ConfigBox
from pathlib import Path

CONFIG_PATH = Path("config/config.yaml")

def read_yaml(path_to_yaml:Path) -> ConfigBox:
    """reads yaml file and returns

    Args:
        path_to_yaml (str): path like input

    Raises:
        ValueError: if yaml file is empty
        e: empty file

    Returns:
        ConfigBox: ConfigBox type
    """
    try:
        with open(path_to_yaml) as yaml_file:
            content = yaml.safe_load(yaml_file)
            return ConfigBox(content)
    except BoxValueError:
        raise ValueError("yaml file is empty")
    except Exception as e:
        raise e
    

def get_config(CONFIG_PATH=CONFIG_PATH):
    """returns ConfigBox type

    Returns:
        ConfigBox: ConfigBox type
    """
    return read_yaml(CONFIG_PATH)


def remove_thinking_from_message(message:str)->str:
    """removes thinking from message
    Args:
        message (str): message
    Returns:
        str: message without thinking
    """
    close_tag = "</think>"
    tag_length = len(close_tag)
    return message[message.index(close_tag) + tag_length:]