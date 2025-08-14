import logging

# Create a logger instance
logger = logging.getLogger("Loftly API")
logger.setLevel(logging.DEBUG)

# Add a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Set a format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# File handler
file_handler = logging.FileHandler("logs/app.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Attach the handler (avoid duplicates)
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)