import logging

import tqdm
import yaml

BATCH_SIZE = 500


class TqdmLoggingHandler(logging.Handler):
    """Redirect all logging messages through tqdm.write()"""

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


# Main logger
level = logging.INFO
formatter = logging.Formatter("%(levelname)s:%(message)s")
handler = TqdmLoggingHandler(level)
handler.setFormatter(formatter)
logger = logging.getLogger("default")
logger.addHandler(handler)
logger.setLevel(level)

# Library loggers
level = logging.WARNING
logging.getLogger("twarc").setLevel(level)
logging.getLogger("telethon").setLevel(level)
logging.getLogger("urllib3.connectionpool").setLevel(level)
logging.getLogger("telethon.network.mtprotosender").disabled = True

with open("config/config.yaml", "r") as stream:
    config = yaml.safe_load(stream)
