import json
from functools import partialmethod


class TgChat:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data['id']
        self.type = data['type']

    def send_text(self, text, **kwargs):
        return self.bot.send_message(self.id, text, **kwargs)

    def _send_to_chat(self, method, **options):
        return self.bot.api_call(
            method,
            chat_id=self.id,
            **options
        )

    send_audio = partialmethod(_send_to_chat, "sendAudio")
    send_photo = partialmethod(_send_to_chat, "sendPhoto")
    send_video = partialmethod(_send_to_chat, "sendVideo")
    send_document = partialmethod(_send_to_chat, "sendDocument")
    send_sticker = partialmethod(_send_to_chat, "sendSticker")
    send_voice = partialmethod(_send_to_chat, "sendVoice")
    send_locaton = partialmethod(_send_to_chat, "sendLocation")

    def forward_message(self, from_chat_id, message_id):
        return self.bot.api_call(
            "forwardMessage",
            chat_id=self.id,
            from_chat_id=from_chat_id,
            message_id=message_id
        )

    def is_group(self):
        return self.type == "group"

class TgMessage:
    """High-level wrapper around Telegram message"""
    def __init__(self, bot, data):
        self.bot = bot
        self.data = data
        self.sender = data['from'].get('username', data['from']['first_name'])
        self.chat_id = data['chat']['id']
        self.chat = TgChat(bot, data['chat'])

    def reply(self, text, markup=None):
        """Reply to this message"""
        return self.chat.send_text(
            text=text,
            disable_web_page_preview='true',
            reply_to_message_id=self.data["message_id"],
            reply_markup=json.dumps(markup)
        )

    def is_group(self):
        return self.chat.is_group()


MESSAGE_TYPES = [
    "location", "photo", "document", "audio", "voice", "sticker", "contact"
]
