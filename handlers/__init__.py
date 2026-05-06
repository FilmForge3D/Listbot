from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.callbacks import button_handler
from handlers.commands import (
    add_command,
    cancel_command,
    draw_command,
    help_command,
    show_panel,
)
from handlers.replies import reply_handler


def register_handlers(application: Application) -> None:
    """Attach all bot handlers to the application."""
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lb", show_panel))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("draw", draw_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(
            filters.REPLY & filters.TEXT & ~filters.COMMAND,
            reply_handler,
        )
    )
