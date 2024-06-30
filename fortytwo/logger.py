import logging

logging.basicConfig(
    level=logging.WARNING,
    #format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("fortytwo.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("FortyTwo")
logger.setLevel(logging.INFO)