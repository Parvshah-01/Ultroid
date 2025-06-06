# Ultroid - UserBot
# Copyright (C) 2021-2023 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
❍ Commands Available -

• `{i}kang <reply to image/sticker/text>`
    Kang the sticker (add to your pack).
"""

import contextlib
import os
import random, string
from secrets import token_hex

from telethon import errors
from telethon.errors.rpcerrorlist import StickersetInvalidError
from telethon.tl.functions.messages import GetStickerSetRequest as GetSticker
from telethon.tl.functions.messages import UploadMediaRequest
from telethon.tl.functions.stickers import AddStickerToSetRequest as AddSticker
from telethon.tl.functions.stickers import CreateStickerSetRequest
from telethon.tl.types import (
    DocumentAttributeSticker,
    InputPeerSelf,
    InputStickerSetEmpty,
)
from telethon.errors.rpcerrorlist import ChatSendInlineForbiddenError
from telethon.tl.types import InputStickerSetItem as SetItem
from telethon.tl.types import InputStickerSetShortName, User
from telethon.utils import get_display_name, get_extension, get_input_document
from telethon.errors import PeerIdInvalidError

from . import LOGS, asst, fetch, udB, ultroid_cmd, get_string,resize_photo_sticker,quotly

async def packExists(packId):
    source = await fetch(f"https://t.me/addstickers/{packId}")
    return (
        not b"""<div class="tgme_page_description">
  A <strong>Telegram</strong> user has created the <strong>Sticker&nbsp;Set</strong>.
</div>"""
        in source
    )

async def GetUniquePackName():
    packName = f"{random.choice(string.ascii_lowercase)}{token_hex(random.randint(4, 8))}_by_{asst.me.username}"
    return await GetUniquePackName() if await packExists(packName) else packName


# TODO: simplify if possible

def getName(sender, packType: str):
    title = f"{get_display_name(sender)}'s Kang Pack"
    if packType != "static":
        title += f" ({packType.capitalize()})"
    return title

async def AddToNewPack(file, emoji, sender_id, title: str):
    sn = await GetUniquePackName()
    return await asst(
        CreateStickerSetRequest(
            user_id=sender_id,
            title=title,
            short_name=sn,
            stickers=[SetItem(file, emoji=emoji)],
            software="@TeamUltroid",
        )
    )

async def inline_query_fallback(ult):
    try:
        result = await ult.client.inline_query(asst.me.username, "startbot")
        if result:
            await result[0].click(ult.chat_id, hide_via=True)
    except (ChatSendInlineForbiddenError):
        await ult.eor(
            f"Inline mode is disabled in this chat.\n\n"
            f"To create or manage your sticker pack, you need to start the assistant bot first.\n\n"
            f"Click the button below to start it:\n"
            f"[Start Bot](https://t.me/{asst.me.username})",
            parse_mode="md"
        )
        return

@ultroid_cmd(pattern="kang", manager=True)
async def kang_func(ult):
    """kang (reply message)
    Create sticker and add to pack"""
    sender = await ult.get_sender()
    if not isinstance(sender, User):
        return
    sender_id = sender.id
    if not ult.is_reply:
        return await ult.eor("`Reply to a message..`", time=5)
    try:
        emoji = ult.text.split(maxsplit=1)[1]
    except IndexError:
        emoji = None
    reply = await ult.get_reply_message()
    ult = await ult.eor(get_string("com_1"))
    type_, dl = "static", None
    if reply.sticker:
        file = get_input_document(reply.sticker)
        if not emoji:
            emoji = reply.file.emoji
        name = reply.file.name
        ext = get_extension(reply.media)
        attr = list(
            filter(
                lambda prop: isinstance(prop, DocumentAttributeSticker),
                reply.document.attributes,
            )
        )
        inPack = attr and not isinstance(attr[0].stickerset, InputStickerSetEmpty)
        with contextlib.suppress(KeyError):
            type_ = {".webm": "video", ".tgs": "animated"}[ext]
        if type_ or not inPack:
            dl = await reply.download_media()
    elif reply.photo:
        dl = await reply.download_media()        
        name = "sticker.webp"
        image = resize_photo_sticker(dl)
        image.save(name, "WEBP") 
        try:
            os.remove(dl)
        except:
            pass                   
        dl = name  
    elif reply.text:
        try:
            reply = await ult.get_reply_message()
            replied_to = await reply.get_reply_message()
            sender_user = await ult.client.get_entity(reply.sender_id)
            quotly_file = await quotly.create_quotly(
            reply, bg="black", reply=replied_to, sender=sender_user)
        except Exception as er:
            return await ult.edit(f"Quotly error: {er}")
        message = await reply.reply("Quotly by Ultroid", file=quotly_file)
        dl = quotly_file
    else:
        return await ult.eor("`Reply to sticker or text to add it in your pack...`")
    if not emoji:
        emoji = "🏵"
    if dl:
        upl = await asst.upload_file(dl)
        file = get_input_document(await asst(UploadMediaRequest(InputPeerSelf(), upl)))
        try:
            os.remove(dl)
        except:
            pass
    get_ = udB.get_key("STICKERS") or {}
    title = getName(sender, type_)
    if not get_.get(sender_id) or not get_.get(sender_id, {}).get(type_):
        try:
            pack = await AddToNewPack(file, emoji, sender.id, title)
        except (ValueError, PeerIdInvalidError) as e:
            await inline_query_fallback(ult)
            return 
        except Exception as er:
            return await ult.eor(str(er))
        sn = pack.set.short_name
        if not get_.get(sender_id):
            get_.update({sender_id: {type_: [sn]}})
        else:
            get_[sender_id].update({type_: [sn]})
        udB.set_key("STICKERS", get_)
        return await ult.edit(
            f"**Kanged Successfully!\nEmoji :** {emoji}\n**Link :** [Click Here](https://t.me/addstickers/{sn})",
            link_preview=False
        )
    name = get_[sender_id][type_][-1]
    try:
        await asst(GetSticker(InputStickerSetShortName(name), hash=0))
    except StickersetInvalidError:
        get_[sender_id][type_].remove(name)
    try:
        await asst(
            AddSticker(InputStickerSetShortName(name), SetItem(file, emoji=emoji))
        )
    except (errors.StickerpackStickersTooMuchError, errors.StickersTooMuchError):
        try:
            pack = await AddToNewPack(file, emoji, sender.id, title)
            sn = pack.set.short_name
        except (ValueError, PeerIdInvalidError) as e:
            await inline_query_fallback(ult)
            return 
        except Exception as er:
            return await ult.eor(str(er))
        get_[sender_id][type_].append(pack.set.short_name)
        udB.set_key("STICKERS", get_)
        return await ult.edit(
            f"**Created New Kang Pack!\nEmoji :** {emoji}\n**Link :** [Click Here](https://t.me/addstickers/{sn})",
            link_preview=False
        )
    except Exception as er:
        LOGS.exception(er)
        return await ult.edit(str(er))
    await ult.edit(
        f"Sticker Added to Pack Successfully\n**Link :** [Click Here](https://t.me/addstickers/{name})",
        link_preview=False
    )


@ultroid_cmd(pattern="listpack", manager=True)
async def do_magic(ult):
    """Get list of sticker packs."""
    ko = udB.get_key("STICKERS") or {}
    if not ko.get(ult.sender_id):
        return await ult.reply("No Sticker Pack Found!")
    al_ = []
    ul = ko[ult.sender_id]
    for _ in ul.keys():
        al_.extend(ul[_])
    msg = "• **Stickers Owned by You!**\n\n"
    for _ in al_:
        try:
            pack = await ult.client(GetSticker(InputStickerSetShortName(_), hash=0))
            msg += f"• [{pack.set.title}](https://t.me/addstickers/{_})\n"
        except StickersetInvalidError:
            for type_ in ["animated", "video", "static"]:
                if ul.get(type_) and _ in ul[type_]:
                    ul[type_].remove(_)
            udB.set_key("STICKERS", ko)
    await ult.reply(msg)
