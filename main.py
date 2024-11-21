import requests
import time
import schedule
import logging
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Load configuration file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Configure logging
log_file = "ip_monitor.log"
logging.basicConfig(
    filename=log_file,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class IPMonitor:
    def __init__(self):
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.cloudflare_zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.dns_record_id = os.getenv("DNS_RECORD_ID")
        self.dns_record_name = os.getenv("DNS_RECORD_NAME")
        self.current_ip = None
        self.ip_check_url = "https://api64.ipify.org"
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
            "title": config["embed_title"],
            "description": config["embed_description_template"].format(ip=new_ip),
            "color": config["embed_color"],
            "footer": {
                "text": config["embed_footer"],
                "icon_url": config.get("embed_footer_icon_url", "")
            }
        }

        # Add author if specified in the config
        if "embed_author" in config:
            embed["author"] = {"name": config["embed_author"]}

        # Add image if specified in the config
        if config.get("embed_image_url"):
            embed["image"] = {"url": config["embed_image_url"]}

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
        schedule.every(5).minutes.do(monitor.check_and_update_ip)

        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logging.critical(f"Critical error occurred: {e}")
