from datetime import time
import db
import user

import pytz

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ConversationHandler,
)

from admin import (
    admin_panel,
    handle_message,
    handle_change_price,
    save_new_price,
    handle_change_period,
    save_new_period,
    handle_change_info,
    save_new_info,
    handle_change_contacts,
    save_new_contacts,
    handle_back_to_admin_menu,
    CHANGE_PRICE,
    CHANGE_PERIOD,
    CHANGE_INFO,
    CHANGE_CONTACTS,
    BACK_BUTTON,
)


def main():
    bot_token = db.get_setting("bot_token")
    application = Application.builder().token(bot_token).build()

    # === Команды ===
    application.add_handler(CommandHandler("start", user.start))
    application.add_handler(CommandHandler("admin", admin_panel))

    admin_settings_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^💳 Изменить цену на подписку$"), handle_change_price
            ),
            MessageHandler(
                filters.Regex("^📞 Изменить период подписки$"), handle_change_period
            ),
            MessageHandler(
                filters.Regex("^ℹ️ Изменить информацию о тренере$"), handle_change_info
            ),
            MessageHandler(
                filters.Regex("^🎥 Изменить контакты$"), handle_change_contacts
            ),
        ],
        states={
            CHANGE_PRICE: [
                MessageHandler(
                    filters.Regex(f"^{BACK_BUTTON}$"), handle_back_to_admin_menu
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_price),
            ],
            CHANGE_PERIOD: [
                MessageHandler(
                    filters.Regex(f"^{BACK_BUTTON}$"), handle_back_to_admin_menu
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_period),
            ],
            CHANGE_INFO: [
                MessageHandler(
                    filters.Regex(f"^{BACK_BUTTON}$"), handle_back_to_admin_menu
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_info),
            ],
            CHANGE_CONTACTS: [
                MessageHandler(
                    filters.Regex(f"^{BACK_BUTTON}$"), handle_back_to_admin_menu
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_contacts),
            ],
        },
        fallbacks=[],
    )
    application.add_handler(admin_settings_conv)

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # === Callback-кнопки ===
    application.add_handler(
        CallbackQueryHandler(user.handle_payment_check, pattern="^check_")
    )
    application.add_handler(
        CallbackQueryHandler(user.init_payment_process, pattern="^init_payment$")
    )
    application.add_handler(CallbackQueryHandler(user.handle_back, pattern="^go_back$"))

    # === Запросы на вступление в группу ===
    application.add_handler(ChatJoinRequestHandler(user.handle_join_request))

    application.job_queue.run_daily(
        user.check_and_remove_expired_subscriptions,
        time=time(hour=14, minute=11, tzinfo=pytz.timezone("Europe/Moscow")),
    )

    # === Запуск бота ===
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
