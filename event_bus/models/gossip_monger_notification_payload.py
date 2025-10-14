import json
from typing import List, Dict, Optional


GOSSIP_MONGER_EXCHANGE: str = "gossip-monger.exchange"
GOSSIP_MONGER_ROUTING_KEY: str = "gossip-monger.notification.requested"


class GossipMongerNotificationPayLoad:
    APP_ID: str = "88ca0bb7-c0d7-4e36-b9e6-ea0e29213593"
    SOURCE_SERVICE_ID: str = "io.opencrafts.chirp"
    EVENT_TYPE: str = "notification.requested"
    REQUEST_ID: str = "00000000-0000-0000-0000-000000000000"

    def __init__(
        self,
        target_user_id: str,
        include_external_user_ids: List[str],
        headings: Optional[Dict[str, str]],
        contents: Dict[str, str],
        subtitle: Optional[Dict[str, str]],
        android_channel_id: Optional[str],
        ios_sound: Optional[str],
        big_picture: Optional[str],
        large_icon: Optional[str],
        small_icon: Optional[str],
        url: Optional[str],
        buttons: Optional[List[Dict[str, str]]],
    ) -> None:
        """
        Initializes a Notification object.
        """
        self.target_user_id = target_user_id
        self.include_external_user_ids = include_external_user_ids
        self.headings = headings
        self.contents = contents
        self.subtitle = subtitle
        self.android_channel_id = android_channel_id
        self.ios_sound = ios_sound
        self.big_picture = big_picture
        self.large_icon = large_icon
        self.small_icon = small_icon
        self.url = url
        self.buttons = buttons

    def to_json(self) -> str:
        """
        Converts the Notification object to a JSON string.
        """
        # Construct the notification part of the JSON
        notification = {
            "app_id": self.APP_ID,
            "headings": self.headings,
            "contents": self.contents,
            "target_user_id": self.target_user_id,
            "include_external_user_ids": self.include_external_user_ids,
            "subtitle": self.subtitle,
            "android_channel_id": self.android_channel_id,
            "ios_sound": self.ios_sound,
            "big_picture": self.big_picture,
            "large_icon": self.large_icon,
            "small_icon": self.small_icon,
            "url": self.url,
            "buttons": self.buttons,
        }

        meta = {
            "event_type": self.EVENT_TYPE,
            "source_service_id": self.SOURCE_SERVICE_ID,
            "request_id": self.REQUEST_ID,
        }

        return json.dumps({"notification": notification, "meta": meta}, indent=4)
