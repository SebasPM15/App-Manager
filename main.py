import customtkinter as ctk
from core.ui_settings import load_ui_scale
from ui.app import App

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    scale = load_ui_scale()
    ctk.set_widget_scaling(scale)
    app = App()
    app.mainloop()
