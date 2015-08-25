import json


class TgMessage:
    """High-level wrapper around Telegram message"""
    def __init__(self, bot, data):
        self.bot = bot
        self.data = data
        self.sender = data['from'].get('username', data['from']['first_name'])
        self.chat_id = data['chat']['id']

    def reply(self, text, markup=None):
        """Reply to this message"""
        return self.bot._send_message(
            chat_id=self.data["chat"]["id"],
            text=text,
            disable_web_page_preview='true',
            reply_to_message_id=self.data["message_id"],
            reply_markup=json.dumps(markup)
        )

    def reply_photo(self, photo, caption=None, markup=None):
        return self.bot._send_photo(
            chat_id=self.data["chat"]["id"],
            photo=photo,
            caption=caption,
            reply_to_message_id=self.data["message_id"],
            reply_markup=json.dumps(markup)
        )

    def is_group(self):
        return "chat" in self.data and "title" in self.data["chat"]


class TextMessage(TgMessage):
    @property
    def text(self):
        return self.data["text"]


class LocationMessage(TgMessage):
    @property
    def location(self):
        return self.data["location"]


class PhotoMessage(TgMessage):
    @property
    def photos(self):
        return self.data["photo"]


class DocumentMessage(TgMessage):
    @property
    def document(self):
        return self.data["document"]


class AudioMessage(TgMessage):
    pass


class StickerMessage(TgMessage):
    pass


class VideoMessage(TgMessage):
    pass


class ContactMessage(TgMessage):
    pass


MESSAGE_TYPES = {
    "location": LocationMessage,
    "photo": PhotoMessage,
    "document": DocumentMessage,
    "audio": AudioMessage,
    "sticker": StickerMessage,
    "video": VideoMessage,
    "contact": ContactMessage
}
