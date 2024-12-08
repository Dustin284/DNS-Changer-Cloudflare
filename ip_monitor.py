import requests
import time
import schedule
import logging
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration Variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
DNS_RECORD_ID = os.getenv("DNS_RECORD_ID")
DNS_RECORD_NAME = os.getenv("DNS_RECORD_NAME")
IP_CHECK_URL = "https://api64.ipify.org"

# Embed Configuration for Discord
EMBED_TITLE = "IP Monitor Alert"
EMBED_DESCRIPTION_TEMPLATE = "The public IP has been updated to: {ip}"
EMBED_COLOR_INFO = 0x808080  # Grey
EMBED_COLOR_SUCCESS = 0x00FF00  # Green
EMBED_COLOR_ERROR = 0xFF0000  # Red
EMBED_FOOTER = "IP Monitor System"
EMBED_FOOTER_ICON_URL = ""  # Optional: Add a URL to an icon

class DiscordLogger(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        log_entry = self.format(record)
        color = (
            EMBED_COLOR_ERROR if record.levelname == "ERROR" else
            EMBED_COLOR_SUCCESS if record.levelname == "INFO" else
            EMBED_COLOR_INFO
        )
        embed = {
            "title": EMBED_TITLE,
            "description": log_entry,
            "color": color,
            "footer": {"text": EMBED_FOOTER, "icon_url": EMBED_FOOTER_ICON_URL}
        }
        data = {"embeds": [embed]}
        try:
            requests.post(self.webhook_url, json=data)
        except requests.RequestException as e:
            print(f"Failed to send log to Discord: {e}")

# Configure Logging
discord_handler = DiscordLogger(DISCORD_WEBHOOK_URL)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
discord_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[discord_handler])

class IPMonitor:
    def __init__(self):
        self.discord_webhook_url = DISCORD_WEBHOOK_URL
        self.cloudflare_api_token = CLOUDFLARE_API_TOKEN
        self.cloudflare_zone_id = CLOUDFLARE_ZONE_ID
        self.dns_record_id = DNS_RECORD_ID
        self.dns_record_name = DNS_RECORD_NAME
        self.ip_check_url = IP_CHECK_URL
        logging.info("IPMonitor initialized.")

    def get_public_ip(self):
        try:
            response = requests.get(self.ip_check_url)
            response.raise_for_status()
            logging.info("Successfully fetched public IP.")
            return response.text.strip()
        except requests.RequestException as e:
            logging.error(f"Error fetching public IP: {e}")
            return None

    def get_dns_record_ip(self):
        url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records/{self.dns_record_id}"
        headers = {
            "Authorization": f"Bearer {self.cloudflare_api_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logging.info("Successfully fetched DNS record IP.")
            return data["result"]["content"]
        except requests.RequestException as e:
            logging.error(f"Error fetching DNS record IP: {e}")
            return None

    def send_discord_notification(self, new_ip):
        embed = {
            "title": EMBED_TITLE,
            "description": EMBED_DESCRIPTION_TEMPLATE.format(ip=new_ip),
            "color": EMBED_COLOR_SUCCESS,
            "footer": {"text": EMBED_FOOTER, "icon_url": EMBED_FOOTER_ICON_URL}
        }
        data = {"embeds": [embed]}
        try:
            response = requests.post(self.discord_webhook_url, json=data)
            response.raise_for_status()
            logging.info("Discord notification sent successfully.")
        except requests.RequestException as e:
            logging.error(f"Error sending Discord notification: {e}")

    def update_cloudflare_dns(self, new_ip):
        url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records/{self.dns_record_id}"
        headers = {
            "Authorization": f"Bearer {self.cloudflare_api_token}",
            "Content-Type": "application/json"
        }
        data = {
            "type": "A",
            "name": self.dns_record_name,
            "content": new_ip,
            "ttl": 1
        }
        try:
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            logging.info("DNS record updated successfully.")
        except requests.RequestException as e:
            logging.error(f"Error updating DNS record: {e}")

    def check_and_update_ip(self):
        public_ip = self.get_public_ip()
        if not public_ip:
            logging.warning("Could not fetch public IP.")
            return

        dns_ip = self.get_dns_record_ip()
        if not dns_ip:
            logging.warning("Could not fetch DNS IP.")
            return

        if public_ip != dns_ip:
            logging.info(f"IP address has changed. Public IP: {public_ip}, DNS IP: {dns_ip}")
            self.send_discord_notification(public_ip)
            self.update_cloudflare_dns(public_ip)
        else:
            logging.info("IP address is unchanged.")

if __name__ == "__main__":
    try:
        monitor = IPMonitor()
        logging.info("Starting IP address monitoring...")
        schedule.every(60).minutes.do(monitor.check_and_update_ip)

        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logging.critical(f"Critical error occurred: {e}")
