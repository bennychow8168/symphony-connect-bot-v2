import re

from jinja2 import Template

from symphony.bdk.core.activity.form import FormReplyActivity, FormReplyContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from .client.connect_client import ConnectApiClient


class PermissionsMainMenuFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = None
        self.action = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "main-menu-form" \
            and context.form_values["action"] in ("view_edit_permissions")

    async def on_activity(self, context: FormReplyContext):
        self.template = Template(open('resources/permissions_view_edit.jinja2').read(), autoescape=True)
        externalNetwork = context.form_values["externalNetwork"]
        connect_permissions = self.getConnectPermissions(externalNetwork)
        connect_entitled_users = self.getConnectEntitledUsers(externalNetwork)
        symphony_user_profiles = dict()
        entitled_users_permissions = dict()

        # Loop through Entitled Users
        for user in connect_entitled_users:
            symphonyId = user['symphonyId']
            # Get Symphony User Details
            try:
                userDet = await self._users.get_user_detail(symphonyId)
                symphony_user_profiles[symphonyId] = userDet['user_attributes']
            except:
                symphony_user_profiles[symphonyId] = {
                    'email_address': ''
                }
                entitled_users_permissions[symphonyId] = []
                continue

            # Get Connect permissions
            advisorEmail = symphony_user_profiles[symphonyId]['email_address']
            entitled_users_permissions[symphonyId] = self.getAdvisorPermission(externalNetwork, advisorEmail)

        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], connect_permissions=connect_permissions,
                                      connect_entitled_users=connect_entitled_users, symphony_user_profiles=symphony_user_profiles, entitled_users_permissions=entitled_users_permissions)

        await self._messages.send_message(context.source_event.stream.stream_id, message)

    def getConnectEntitledUsers(self, externalNetwork):
        status, result = self.connect_client.list_entitlements(externalNetwork)
        if status == 'OK':
            if 'entitlements' in result and len(result['entitlements']) > 0:
                return result['entitlements']

        return []

    def getConnectPermissions(self, externalNetwork):
        status, result = self.connect_client.list_permission(externalNetwork)
        if status == 'OK':
            if 'permissions' in result and len(result['permissions']) > 0:
                output = []
                for p in result['permissions']:
                    if isinstance(p, dict) and 'permissionName' in p:
                        output.append(p['permissionName'])
                    else:
                        output.append(p)
                return output

        return []

    def getAdvisorPermission(self, externalNetwork, advisorEmail):
        status, result = self.connect_client.get_advisor_permission(externalNetwork, advisorEmail)
        if status == 'OK':
            if 'permissions' in result and len(result['permissions']) > 0:
                output = []
                for p in result['permissions']:
                    if isinstance(p, dict) and 'permissionName' in p:
                        output.append(p['permissionName'])
                    else:
                        output.append(p)
                return output

        return []


class PermissionsViewEditFormReplyActivity(FormReplyActivity):

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = None
        self.action = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "permissions-view-edit-form" \
            and context.form_values["action"].startswith("edit_")

    async def on_activity(self, context: FormReplyContext):
        self.template = Template(open('resources/permissions_edit_user.jinja2').read(), autoescape=True)
        symphonyId = re.search("(edit_)(.+)", context.form_values["action"]).group(2)
        externalNetwork = context.form_values["externalNetwork"]

        # Get Symphony User Details
        try:
            userDet = await self._users.get_user_detail(symphonyId)
            user_profile = userDet['user_attributes']
            advisorEmail = user_profile['email_address']
        except:
            message = f'<messageML>Fail to get user email for {symphonyId}</messageML>'
            await self._messages.send_message(context.source_event.stream.stream_id, message)
            return

        connect_permissions = self.getConnectPermissions(externalNetwork)
        user_permissions = self.getAdvisorPermission(externalNetwork, advisorEmail)

        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], connect_permissions=connect_permissions, user_permissions=user_permissions, user_profile=user_profile)
        await self._messages.send_message(context.source_event.stream.stream_id, message)

    def getConnectPermissions(self, externalNetwork):
        status, result = self.connect_client.list_permission(externalNetwork)
        if status == 'OK':
            if 'permissions' in result and len(result['permissions']) > 0:
                output = []
                for p in result['permissions']:
                    if isinstance(p, dict) and 'permissionName' in p:
                        output.append(p['permissionName'])
                    else:
                        output.append(p)
                return output

        return []

    def getAdvisorPermission(self, externalNetwork, advisorEmail):
        status, result = self.connect_client.get_advisor_permission(externalNetwork, advisorEmail)
        if status == 'OK':
            if 'permissions' in result and len(result['permissions']) > 0:
                output = []
                for p in result['permissions']:
                    if isinstance(p, dict) and 'permissionName' in p:
                        output.append(p['permissionName'])
                    else:
                        output.append(p)
                return output

        return []


class PermissionsEditUserFormReplyActivity(FormReplyActivity):

    def __init__(self, messages: MessageService, users: UserService, connect_client: ConnectApiClient):
        self._messages = messages
        self._users = users
        self.connect_client = connect_client
        self.template = None
        self.action = None

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_id == "permissions-edit-user-form" \
            and "new_permissions" in context.form_values

    async def on_activity(self, context: FormReplyContext):
        self.template = Template(open('resources/permissions_edit_user_result.jinja2').read(), autoescape=True)
        externalNetwork = context.form_values["externalNetwork"]
        advisorEmail = context.form_values["advisorEmail"]
        permission_list = context.form_values["new_permissions"]
        permission_results = dict()

        for p in permission_list:
            status, result = self.connect_client.add_permission(externalNetwork, advisorEmail, p)
            output = {
                "status": status,
                "result": result
            }
            permission_results[p] = output

        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], advisorEmail=advisorEmail, permission_results=permission_results)
        await self._messages.send_message(context.source_event.stream.stream_id, message)


    def addPermission(self, externalNetwork, advisorEmail, permissionName):
        status, result = self.connect_client.add_permission(externalNetwork, advisorEmail, permissionName)
        if status == 'OK':
            if 'permissions' in result and len(result['permissions']) > 0:
                output = []
                for p in result['permissions']:
                    if isinstance(p, dict) and 'permissionName' in p:
                        output.append(p['permissionName'])
                    else:
                        output.append(p)
                return output

        return []