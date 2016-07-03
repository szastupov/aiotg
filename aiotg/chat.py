import json
import logging
from functools import partialmethod


logger = logging.getLogger("aiotg")


class Chat:
    """
    Wrapper for telegram chats, passed to most callbacks
    """

    def send_text(self, text, **options):
        """
        Send a text message to the chat, for available options see
        https://core.telegram.org/bots/api#sendmessage
        """
        return self.bot.send_message(self.id, text, **options)

    def reply(self, text, markup={}, parse_mode=None):
        return self.send_text(
            text,
            reply_to_message_id=self.message["message_id"],
            disable_web_page_preview='true',
            reply_markup=json.dumps(markup),
            parse_mode=parse_mode
        )

    def edit_text(self, message_id, text, markup={}, parse_mode=None):
        return self.bot.edit_message_text(
            self.id,
            message_id,
            text,
            reply_markup=json.dumps(markup),
            parse_mode=parse_mode
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
    send_location = partialmethod(_send_to_chat, "sendLocation")
    send_chat_action = partialmethod(_send_to_chat, "sendChatAction")

    def forward_message(self, from_chat_id, message_id):
        return self.bot.api_call(
            "forwardMessage",
            chat_id=self.id,
            from_chat_id=from_chat_id,
            message_id=message_id
        )

    def is_group(self):
        return self.type == "group"

    def __init__(self, bot, chat_id, chat_type="private", src_message=None):
        self.bot = bot
        self.message = src_message
        sender = src_message['from'] if src_message else {"first_name": "N/A"}
        self.sender = Sender(sender)
        self.id = chat_id
        self.type = chat_type

    @staticmethod
    def from_message(bot, message):
        chat = message["chat"]
        return Chat(bot, chat["id"], chat["type"], message)


class TgChat(Chat):
    def __init__(self, *args, **kwargs):
        logger.warning("TgChat is depricated, use Chat instead")
        super().__init__(*args, **kwargs)


class Sender(dict):
    """A small wrapper for sender info, mostly used for logging"""

    def __repr__(self):
        uname = " (%s)" % self["username"] if "username" in self else ""
        return self['first_name'] + uname


class TgSender(Sender):
    def __init__(self, *args, **kwargs):
        logger.warning("TgSender is depricated, use Sender instead")
        super().__init__(*args, **kwargs)
