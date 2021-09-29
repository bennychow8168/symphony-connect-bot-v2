import re

from jinja2 import Template

from symphony.bdk.core.activity.form import FormReplyActivity, FormReplyContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from .client.connect_client import ConnectApiClient


class EntitlementsMainMenuFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, connect_client: ConnectApiClient):
        self._messages = messages
        self.connect_client = connect_client
        self.template = Template(open('resources/entitlements_add.jinja2').read(), autoescape=True)
        self.action = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "main-menu-form" \
            and context.form_values["action"] in ("add_entitlements", "view_delete_entitlements")

    async def on_activity(self, context: FormReplyContext):
        self.action = context.form_values["action"]
        if self.action == "add_entitlements":
            self.template = Template(open('resources/entitlements_add.jinja2').read(), autoescape=True)
            message = self.template.render(externalNetwork=context.form_values["externalNetwork"])
        else:
            self.template = Template(open('resources/entitlements_view_delete.jinja2').read(), autoescape=True)
            userList = self.getConnectEntitledUsers(context.form_values["externalNetwork"])
            message = self.template.render(externalNetwork=context.form_values["externalNetwork"], userList=userList)

        await self._messages.send_message(context.source_event.stream.stream_id, message)

    def getConnectEntitledUsers(self, externalNetwork):
        status, result = self.connect_client.list_entitlements(externalNetwork)
        if status == 'OK':
            if 'entitlements' in result and len(result['entitlements']) > 0:
                return result['entitlements']

        return []


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
            and context.form_values["userlist"]

    async def on_activity(self, context: FormReplyContext):
        userList = context.form_values["userlist"]
        externalNetwork = context.form_values["externalNetwork"]
        user_dict = dict()
        result_dict = dict()

        for symphonyId in userList:
            # Get Symphony User Details
            try:
                userDet = await self._users.get_user_detail(symphonyId)
                user_dict[symphonyId] = userDet['user_attributes']
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