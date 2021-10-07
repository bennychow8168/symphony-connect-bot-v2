from jinja2 import Template

from symphony.bdk.core.config.model.bdk_config import BdkConfig
from symphony.bdk.core.activity.command import SlashCommandActivity, CommandContext
from symphony.bdk.core.activity.form import FormReplyActivity, FormReplyContext
from symphony.bdk.core.service.message.message_service import MessageService

class MainCommandActivity(SlashCommandActivity):
    """@bot-name /start
    """
    command_name = "/start"

    def __init__(self, messages: MessageService, config: BdkConfig):
        super().__init__(self.command_name, True, self.show_main_menu, "Show Main Menu")
        self._messages = messages
        self._config = config
        self.template = Template(open('resources/main_menu.jinja2').read(), autoescape=True)

    async def show_main_menu(self, context: CommandContext):
        # Get list of defined external networks from config
        extNetwork_list = list(self._config.context.keys())
        message = self.template.render(extNetwork_list=extNetwork_list)
        await self._messages.send_message(context.stream_id, message)


class RestartMainFormReplyActivity(FormReplyActivity):
    # Sends back the selected value on form submission

    def __init__(self, messages: MessageService, config: BdkConfig):
        self._messages = messages
        self._config = config
        self.template = Template(open('resources/main_menu.jinja2').read(), autoescape=True)

    def matches(self, context: FormReplyContext) -> bool:
        return context.form_values["action"] == "restart_main"

    async def on_activity(self, context: FormReplyContext):
        extNetwork_list = list(self._config.context.keys())
        message = self.template.render(extNetwork_list=extNetwork_list)
        await self._messages.send_message(context.source_event.stream.stream_id, message)


class HelpCommand(SlashCommandActivity):
    """The help command is a particular CommandActivity which returns the list of all commands available for the
    specific bot
    The Slash command is triggered if we receive a MESSAGESENT event with message text:
      - "@{bot_display name} /help"
    """

    def __init__(self, messages: MessageService):
        super().__init__("/help", True, None, "List available commands")
        self._messages = messages
        self.template = Template(open('resources/help_menu.jinja2').read(), autoescape=True)

    async def on_activity(self, context: CommandContext):
        bot_displayname = "@" + context.bot_display_name
        message = self.template.render(bot_displayname=bot_displayname)
        await self._messages.send_message(context.stream_id, message)