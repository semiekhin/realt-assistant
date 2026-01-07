"""
Bot handlers
"""
from bot.handlers.start import (
    handle_start,
    handle_help,
    handle_menu,
    handle_my_properties
)

from bot.handlers.add_property import (
    handle_add_property_start,
    handle_property_name,
    handle_file_upload,
    handle_files_done,
    handle_confirm_property,
    handle_property_correction,
    handle_cancel
)

from bot.handlers.query import (
    handle_open_property,
    handle_download_file,
    handle_all_files,
    handle_property_summary,
    handle_delete_property,
    handle_confirm_delete,
    handle_property_query,
    handle_search_all,
    handle_search_start
)

from bot.handlers.kp import (
    handle_kp_for_property,
    handle_kp_generate
)
