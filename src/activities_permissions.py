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
        return context.form_id in ("main-menu-form", "permissions-view-edit-form") \
            and context.form_values["action"] in ("view_edit_permissions", "next_page", "prev_page")

    async def on_activity(self, context: FormReplyContext):
        self.template = Template(open('resources/permissions_view_edit.jinja2').read(), autoescape=True)
        externalNetwork = context.form_values["externalNetwork"]
        self.action = context.form_values["action"]
        if self.action == "next_page":
            page_cursor = context.form_values['next_cursor']
        elif self.action == "prev_page":
            page_cursor = context.form_values['prev_cursor']
        else:
            page_cursor = ''
        connect_permissions = self.getConnectPermissions(externalNetwork)
        connect_entitled_users, next_cursor, prev_cursor = self.getConnectEntitledUsers(externalNetwork, page_cursor)
        symphony_user_profiles = await self.getSymphonyUserDetails(connect_entitled_users)
        entitled_users_permissions = dict()

        # Loop through Entitled Users
        for user in connect_entitled_users:
            symphonyId = user['symphonyId']

            # Get Connect permissions
            advisorEmail = symphony_user_profiles[symphonyId]['email_address']
            entitled_users_permissions[symphonyId] = self.getAdvisorPermission(externalNetwork, advisorEmail)

        message = self.template.render(externalNetwork=context.form_values["externalNetwork"], connect_permissions=connect_permissions,
                                      connect_entitled_users=connect_entitled_users, symphony_user_profiles=symphony_user_profiles, entitled_users_permissions=entitled_users_permissions,
                                       next_cursor=next_cursor, prev_cursor=prev_cursor)

        await self._messages.send_message(context.source_event.stream.stream_id, message)

    def getConnectEntitledUsers(self, externalNetwork, page_cursor):
        status, result, next_cursor, prev_cursor = self.connect_client.list_entitlements(externalNetwork, page_cursor)
        if status == 'OK':
            if 'entitlements' in result and len(result['entitlements']) > 0:
                return result['entitlements'], next_cursor, prev_cursor

        return [], '', ''

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
            userDet = await self._users.list_users_by_ids(user_ids=[symphonyId])
            if 'users' in userDet:
                user_profile = userDet['users'][0]
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
            and ("new_permissions" in context.form_values or "del_permissions" in context.form_values)

    async def on_activity(self, context: FormReplyContext):
        self.template = Template(open('resources/permissions_edit_user_result.jinja2').read(), autoescape=True)
        externalNetwork = context.form_values["externalNetwork"]
        advisorEmail = context.form_values["advisorEmail"]
        del_permission_list = []
        add_permission_list = []
        permission_results = dict()

        if "del_permissions" in context.form_values:
            if isinstance(context.form_values["del_permissions"], list):
                del_permission_list = context.form_values["del_permissions"]
            else:
                del_permission_list.append(context.form_values["del_permissions"])

        if "new_permissions" in context.form_values:
            if isinstance(context.form_values["new_permissions"], list):
                add_permission_list = context.form_values["new_permissions"]
            else:
                add_permission_list.append(context.form_values["new_permissions"])

        for p1 in del_permission_list:
            status, result = self.connect_client.delete_permission(externalNetwork, advisorEmail, p1)
            output = {
                "status": status,
                "result": result
            }
            permission_results[p1] = output

        for p2 in add_permission_list:
            status, result = self.connect_client.add_permission(externalNetwork, advisorEmail, p2)
            output = {
                "status": status,
                "result": result
            }
            permission_results[p2] = output

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