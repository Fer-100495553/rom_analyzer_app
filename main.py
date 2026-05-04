from __future__ import annotations

import customtkinter as ctk
import settings_manager
from gui import App


def main() -> None:
    ctk.set_appearance_mode(settings_manager.get("theme"))
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
