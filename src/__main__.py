#!/usr/bin/env python3
import asyncio
import logging.config
from pathlib import Path

from symphony.bdk.core.config.loader import BdkConfigLoader
from symphony.bdk.core.service.datafeed.real_time_event_listener import RealTimeEventListener
from symphony.bdk.core.symphony_bdk import SymphonyBdk
from symphony.bdk.gen.agent_model.v4_initiator import V4Initiator
from symphony.bdk.gen.agent_model.v4_message_sent import V4MessageSent

from .activities_main import MainCommandActivity, HelpCommand
from .activities_entitlement import EntitlementsMainMenuFormReplyActivity, EntitlementsDeleteFormReplyActivity, EntitlementsAddFormReplyActivity
from .activities_permissions import PermissionsMainMenuFormReplyActivity, PermissionsViewEditFormReplyActivity, PermissionsEditUserFormReplyActivity
from .client.connect_client import ConnectApiClient

# Configure logging
current_dir = Path(__file__).parent.parent
logging_conf = Path.joinpath(current_dir, 'resources', 'logging.conf')
logging.config.fileConfig(logging_conf, disable_existing_loggers=False)


async def run():
    config = BdkConfigLoader.load_from_file(Path.joinpath(current_dir, 'resources', 'config.yaml'))

    # Init Conenct API Client
    connect_client = ConnectApiClient(config)

    async with SymphonyBdk(config) as bdk:
        datafeed_loop = bdk.datafeed()
        datafeed_loop.subscribe(MessageListener())

        activities = bdk.activities()
        activities.register(MainCommandActivity(bdk.messages()))
        activities.register(HelpCommand(bdk.messages()))
        activities.register(EntitlementsMainMenuFormReplyActivity(bdk.messages(), connect_client))
        activities.register(EntitlementsDeleteFormReplyActivity(bdk.messages(), connect_client))
        activities.register(EntitlementsAddFormReplyActivity(bdk.messages(), bdk.users(), connect_client))
        activities.register(PermissionsMainMenuFormReplyActivity(bdk.messages(), bdk.users(), connect_client))
        activities.register(PermissionsViewEditFormReplyActivity(bdk.messages(), bdk.users(), connect_client))
        activities.register(PermissionsEditUserFormReplyActivity(bdk.messages(), bdk.users(), connect_client))

        # Start the datafeed read loop
        await datafeed_loop.start()


class MessageListener(RealTimeEventListener):
    async def on_message_sent(self, initiator: V4Initiator, event: V4MessageSent):
        logging.debug("Message received from %s: %s",
            initiator.user.display_name, event.message.message)


# Start the main asyncio run
try:
    logging.info("Running bot application...")
    asyncio.run(run())
except KeyboardInterrupt:
    logging.info("Ending bot application")
