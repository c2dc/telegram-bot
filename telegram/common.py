import logging

import yaml

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("twarc").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("telethon.network.mtprotosender").disabled = True

logger = logging.getLogger("default")


with open("config.yaml", "r") as stream:
    config = yaml.safe_load(stream)
