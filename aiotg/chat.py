import json

from functools import partialmethod


class TgSender(dict):
    def __repr__(self):
        uname = " (%s)" % self["username"] if "username" in self else ""
        return self['first_name'] + uname


class TgChat:
    def __init__(self, bot, chat_id, chat_type="private", src_message=None):
        self.bot = bot
        self.message = src_message
        sender = src_message['from'] if src_message else {"first_name": "N/A"}
        self.sender = TgSender(sender)
        self.id = chat_id
        self.type = chat_type

    @staticmethod
    def from_message(bot, message):
        chat = message["chat"]
        return TgChat(bot, chat["id"], chat["type"], message)

    def send_text(self, text, **kwargs):
        return self.bot.send_message(self.id, text, **kwargs)

    def reply(self, text, markup=None):
        return self.send_text(text,
            reply_to_message_id=self.message["message_id"],
            disable_web_page_preview='true',
            reply_markup=json.dumps(markup)
        )

    def _send_to_chat(self, method, **options):
        return self.bot.api_call(
            method,
            chat_id=str(self.id),
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
