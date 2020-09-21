# Copyright (C) 2020 TeamDerUntergang.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from sqlalchemy.exc import IntegrityError

from sedenbot.moduller.chat import is_muted
from sedenbot import PM_COUNT, KOMUT, PM_AUTO_BAN, PM_LAST_MSG, LOGS, PM_UNAPPROVED, PM_MSG_COUNT
from sedenecem.core import sedenify, send_log, me, edit, reply, get_translation
# ========================= CONSTANTS ============================
DEF_UNAPPROVED_MSG = PM_UNAPPROVED or get_translation('pmpermitMessage', ['`'])
# =================================================================


@sedenify(incoming=True, outgoing=False, disable_edited=True,
          disable_notify=True, group=False, compat=False, bot=False)
def permitpm(client, message):
    if message.from_user and message.from_user.is_self:
        message.continue_propagation()

    UNAPPROVED_MSG = DEF_UNAPPROVED_MSG
    if 'PM_USER_MSG' in globals() and PM_USER_MSG:
        UNAPPROVED_MSG = PM_USER_MSG

    if not PM_AUTO_BAN:
        message.continue_propagation()
    else:
        if auto_accept(client, message):
            return

        self_user = me[0]
        if message.chat.id not in [self_user.id, 777000]:
            try:
                from sedenecem.sql.pm_permit_sql import is_approved
            except BaseException:
                pass

            apprv = is_approved(message.chat.id)
            notifsoff = is_muted(-1)

            if not apprv and message.text != UNAPPROVED_MSG:
                if message.chat.id in PM_LAST_MSG:
                    prevmsg = PM_LAST_MSG[message.chat.id]
                    if message.text != prevmsg:
                        for message in _find_unapproved_msg(
                                client, message.chat.id):
                            message.delete()
                        if PM_COUNT[message.chat.id] < (PM_MSG_COUNT - 1):
                            ret = reply(message, UNAPPROVED_MSG)
                            PM_LAST_MSG[message.chat.id] = ret.text
                else:
                    ret = reply(message, UNAPPROVED_MSG)
                    PM_LAST_MSG[message.chat.id] = ret.text

                if notifsoff:
                    client.read_history(message.chat.id)

                if message.chat.id not in PM_COUNT:
                    PM_COUNT[message.chat.id] = 1
                else:
                    PM_COUNT[message.chat.id] = PM_COUNT[message.chat.id] + 1

                if PM_COUNT[message.chat.id] > (PM_MSG_COUNT - 1):
                    reply(message, f'`{get_translation("pmpermitBlock")}`')

                    try:
                        del PM_COUNT[message.chat.id]
                        del PM_LAST_MSG[message.chat.id]
                    except BaseException:
                        pass

                    client.block_user(message.chat.id)

                    send_log(
                        get_translation(
                            "pmpermitLog", [
                                message.chat.first_name, message.chat.id]))

    message.continue_propagation()


def auto_accept(client, message):
    self_user = me[0]
    if message.chat.id not in [self_user.id, 777000]:
        try:
            from sedenecem.sql.pm_permit_sql import approve, is_approved
        except BaseException:
            return False

        chat = message.chat
        if is_approved(chat.id):
            return True

        for msg in client.get_history(chat.id, limit=3):
            if chat.id in PM_LAST_MSG and msg.text != PM_LAST_MSG[chat.id] and msg.from_user.is_self:
                try:
                    del PM_COUNT[chat.id]
                    del PM_LAST_MSG[chat.id]
                except BaseException:
                    pass

                try:
                    approve(chat.id)
                    for message in _find_unapproved_msg(client, chat.id):
                        message.delete()
                    send_log(
                        get_translation(
                            "pmAutoAccept", [
                                chat.first_name, chat.id]))
                    return True
                except BaseException:
                    pass

    return False


@sedenify(outgoing=True, pattern="^.notifoff$")
def notifoff(message):
    try:
        from sedenecem.sql.keep_read_sql import kread
    except BaseException:
        edit(message, f'`{get_translation("nonSqlMode")}`')
        return

    kread(str(-1))
    edit(message, f'`{get_translation("pmNotifOff")}`')


@sedenify(outgoing=True, pattern="^.notifon$")
def notifon(message):
    try:
        from sedenecem.sql.keep_read_sql import unkread
    except BaseException:
        edit(message, f'`{get_translation("nonSqlMode")}`')
        return

    unkread(str(-1))
    edit(message, f'`{get_translation("pmNotifOn")}`')


@sedenify(outgoing=True, pattern="^.approve$", compat=False)
def approvepm(client, message):
    UNAPPROVED_MSG = DEF_UNAPPROVED_MSG
    if 'PM_USER_MSG' in globals() and PM_USER_MSG:
        UNAPPROVED_MSG = PM_USER_MSG
    try:
        from sedenecem.sql.pm_permit_sql import approve
    except BaseException:
        edit(message, f'`{get_translation("nonSqlMode")}`')
        return

    if message.reply_to_message:
        reply = message.reply_to_message
        replied_user = reply.from_user
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        uid = replied_user.id
    else:
        aname = message.chat
        if not aname.type == 'private':
            edit(message, f'`{get_translation("pmApproveError")}`')
            return
        name0 = aname.first_name
        uid = aname.id

    try:
        approve(uid)
    except IntegrityError:
        edit(message, f'`{get_translation("pmApproveError2")}`')
        return

    edit(message, get_translation("pmApproveSuccess", [name0, uid, '`']))

    for message in _find_unapproved_msg(client, message.chat.id):
        message.delete()

    send_log(get_translation("pmApproveLog", [name0, uid]))


@sedenify(outgoing=True, pattern="^.disapprove$")
def disapprovepm(message):
    try:
        from sedenecem.sql.pm_permit_sql import dissprove
    except BaseException:
        edit(message, f'`{get_translation("nonSqlMode")}`')
        return

    if message.reply_to_message:
        reply = message.reply_to_message
        replied_user = reply.from_user
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        uid = replied_user.id
    else:
        aname = message.chat
        if not aname.type == 'private':
            edit(message, f'`{get_translation("pmApproveError")}`')
            return
        name0 = aname.first_name
        uid = aname.id

    dissprove(uid)

    edit(message, get_translation("pmDisapprove", [name0, uid, '`']))

    send_log(get_translation("pmDisapprove", [name0, uid, '`']))


@sedenify(pattern="^.block$", compat=False)
def blockpm(client, message):
    if message.reply_to_message:
        reply = message.reply_to_message
        replied_user = reply.from_user
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        uid = replied_user.id
    else:
        aname = message.chat
        if not aname.type == 'private':
            edit(message, f'`{get_translation("pmApproveError")}`')
            return
        name0 = aname.first_name
        uid = aname.id

    client.block_user(uid)

    edit(message, f'`{get_translation("pmBlocked")}`')

    try:
        from sedenecem.sql.pm_permit_sql import dissprove
        dissprove(uid)
    except BaseException:
        pass

    send_log(get_translation("pmBlockedLog", [name0, uid]))


@sedenify(pattern="^.unblock$", compat=False)
def unblockpm(client, message):
    if message.reply_to_message:
        reply = message.reply_to_message
        replied_user = reply.from_user
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        uid = replied_user.id
        client.unblock_user(uid)
        edit(message, f'`{get_translation("pmUnblocked")}`')

        send_log(get_translation("pmUnblockedLog", [name0, replied_user.id]))
    else:
        edit(message, f'`{get_translation("pmUnblockedUsage")}`')


@sedenify(pattern="^.(rem|set)permitmsg")
def set_permit_msg(message):
    txt = message.text.split(' ', 1)
    act = txt[0][1:4]
    global PM_USER_MSG
    if act == 'rem':
        PM_USER_MSG = None
        UNAPPROVED_MSG = DEF_UNAPPROVED_MSG
        edit(message, get_translation("remPermitMsg", ['`', UNAPPROVED_MSG]))
    elif len(txt) < 2:
        edit(message, f'`{get_translation("setPermitUsage")}`')
    else:
        PM_USER_MSG = UNAPPROVED_MSG = txt[1]
        edit(message, get_translation("setPermitMsg", ['`', UNAPPROVED_MSG]))


def _find_unapproved_msg(client, chat_id):
    UNAPPROVED_MSG = DEF_UNAPPROVED_MSG
    if 'PM_USER_MSG' in globals() and PM_USER_MSG:
        UNAPPROVED_MSG = PM_USER_MSG
    return client.search_messages(
        chat_id,
        from_user='me',
        limit=10,
        query=UNAPPROVED_MSG)


KOMUT.update({"pmpermit": get_translation("pmpermitInfo")})
