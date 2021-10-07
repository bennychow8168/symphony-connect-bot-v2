import re

from jinja2 import Template

from symphony.bdk.core.activity.form import FormReplyActivity, FormReplyContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from .client.connect_client import ConnectApiClient


class EntitlementsMainMenuFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = Template(open('resources/entitlements_add.jinja2').read(), autoescape=True)
        self.action = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id in ("main-menu-form", "entitlements-view-delete-form") \
            and context.form_values["action"] in ("add_entitlements", "search_entitlements", "view_delete_entitlements", "next_page", "prev_page")

    async def on_activity(self, context: FormReplyContext):
        self.action = context.form_values["action"]
        if self.action == "add_entitlements":
            self.template = Template(open('resources/entitlements_add.jinja2').read(), autoescape=True)
            message = self.template.render(externalNetwork=context.form_values["externalNetwork"])
        elif self.action == "search_entitlements":
            self.template = Template(open('resources/entitlements_search.jinja2').read(), autoescape=True)
            message = self.template.render(externalNetwork=context.form_values["externalNetwork"])
        else:
            if self.action == "next_page":
                page_cursor = context.form_values['next_cursor']
            elif self.action == "prev_page":
                page_cursor = context.form_values['prev_cursor']
            else:
                page_cursor = ''
            self.template = Template(open('resources/entitlements_view_delete.jinja2').read(), autoescape=True)
            userList, next_cursor, prev_cursor = self.getConnectEntitledUsers(context.form_values["externalNetwork"], page_cursor)
            symphony_user_profiles = await self.getSymphonyUserDetails(userList)
            message = self.template.render(externalNetwork=context.form_values["externalNetwork"], userList=userList, next_cursor=next_cursor, prev_cursor=prev_cursor, symphony_user_profiles=symphony_user_profiles)

        await self._messages.send_message(context.source_event.stream.stream_id, message)

    def getConnectEntitledUsers(self, externalNetwork, page_cursor):
        status, result, next_cursor, prev_cursor = self.connect_client.list_entitlements(externalNetwork, page_cursor)
        if status == 'OK':
            if 'entitlements' in result and len(result['entitlements']) > 0:
                return result['entitlements'], next_cursor, prev_cursor

        return [], '', ''

    async def getSymphonyUserDetails(self, userList):
        userIds = []
        resultDict = dict()
        for u1 in userList:
            userIds.append(u1['symphonyId'])

        output = await self._users.list_users_by_ids(user_ids=userIds)

        if 'users' in output:
            for u2 in output['users']:
                resultDict[str(u2['id'])] = u2

        return resultDict


class EntitlementsDeleteFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, connect_client: ConnectApiClient):
        self._messages = messages
        self.connect_client = connect_client

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "entitlements-view-delete-form" \
            and context.form_values["action"].startswith("del_")

    async def on_activity(self, context: FormReplyContext):
        symphonyId = re.search("(del_)(.+)", context.form_values["action"]).group(2)
        status, result = self.connect_client.delete_entitlement(context.form_values["externalNetwork"], symphonyId)
        if status == 'OK':
            await self._messages.send_message(context.source_event.stream.stream_id, f"<messageML>Successfully removed user from {context.form_values['externalNetwork']} entitlement</messageML>")
        else:
            await self._messages.send_message(context.source_event.stream.stream_id, f"<messageML>Error removing user!</messageML>")


class EntitlementsAddFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "entitlements-add-form" \
            and context.form_values["userlist"] \
            and context.form_values["action"] != "restart_main"

    async def on_activity(self, context: FormReplyContext):
        userList = context.form_values["userlist"]
        externalNetwork = context.form_values["externalNetwork"]
        user_dict = dict()
        result_dict = dict()

        for symphonyId in userList:
            # Get Symphony User Details
            try:
                output = await self._users.list_users_by_ids(user_ids=[symphonyId])
                if 'users' in output:
                    userDet = output['users'][0]
                    user_dict[symphonyId] = userDet
                else:
                    user_dict[symphonyId] = {
                        'display_name': symphonyId,
                        'email_address': ''
                    }
                    result_dict[symphonyId] = "ERROR: Invalid User"

            except:
                user_dict[symphonyId] = {
                    'display_name': symphonyId,
                    'email_address': ''
                }
                result_dict[symphonyId] = "ERROR: Invalid User"
                continue

            # Call Connect Add Entitlement
            status, result = self.connect_client.add_entitlement(externalNetwork, symphonyId)
            if status == 'OK':
                result_dict[symphonyId] = 'User successfully added'
            else:
                result_dict[symphonyId] = result

        # Render and send result
        self.template = Template(open('resources/entitlements_add_result.jinja2').read(), autoescape=True)
        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], user_dict=user_dict, result_dict = result_dict)
        await self._messages.send_message(context.source_event.stream.stream_id, message)


class EntitlementsSearchFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "entitlements-search-form" \
            and context.form_values["userlist"] \
            and context.form_values["action"] != "restart_main"

    async def on_activity(self, context: FormReplyContext):
        userList = context.form_values["userlist"]
        externalNetwork = context.form_values["externalNetwork"]
        user_dict = dict()
        result_dict = dict()

        for symphonyId in userList:
            # Get Symphony User Details
            try:
                output = await self._users.list_users_by_ids(user_ids=[symphonyId])
                if 'users' in output:
                    userDet = output['users'][0]
                    user_dict[symphonyId] = userDet

                    # Check user Entitlement status
                    status, result = self.connect_client.get_entitlement(externalNetwork, symphonyId)
                    if status == 'OK':
                        result_dict[symphonyId] = result
                    else:
                        result_dict[symphonyId] = "ERROR"
                else:
                    user_dict[symphonyId] = {
                        'display_name': symphonyId,
                        'email_address': ''
                    }
                    result_dict[symphonyId] = "ERROR"

            except:
                user_dict[symphonyId] = {
                    'display_name': symphonyId,
                    'email_address': ''
                }
                result_dict[symphonyId] = "ERROR"
                continue

        # Render and send result
        self.template = Template(open('resources/entitlements_view_delete.jinja2').read(), autoescape=True)
        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], userDict=result_dict,
                                       next_cursor='', prev_cursor='',
                                       symphony_user_profiles=user_dict)
        await self._messages.send_message(context.source_event.stream.stream_id, message)