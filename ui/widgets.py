import customtkinter as ctk
from ui.theme import Colors, Fonts, Dims


def font(size: int = Fonts.SIZE_BASE, weight: str = "normal", mono: bool = False) -> ctk.CTkFont:
    family = Fonts.FAMILY_MONO if mono else Fonts.FAMILY_PRIMARY
    return ctk.CTkFont(family=family, size=size, weight=weight)


def make_panel(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=Colors.PANEL,
        border_width=1,
        border_color=Colors.LINE,
        corner_radius=Dims.PANEL_RADIUS,
        **kwargs,
    )


def make_eyebrow(parent, text: str, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text.upper(),
        font=font(Fonts.SIZE_XS, "bold"),
        text_color=Colors.TEXT_DIM,
        anchor="w",
        **kwargs,
    )


def make_button(parent, text: str, command, kind: str = "secondary", height: int = Dims.BTN_HEIGHT, **kwargs) -> ctk.CTkButton:
    styles = {
        "primary":   (Colors.PRIMARY, Colors.PRIMARY_HOVER, "#6699dc", "#ffffff"),
        "secondary": (Colors.SECONDARY, Colors.SECONDARY_HOVER, Colors.LINE, "#b7c6d7"),
        "danger":    (Colors.DANGER_BG, Colors.DANGER_HOVER, Colors.DANGER_LINE, Colors.DANGER_TEXT),
        "ghost":     ("transparent", Colors.SURFACE, Colors.LINE, Colors.TEXT_MUTED),
    }
    fg, hover, border, text_color = styles[kind]
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=fg,
        hover_color=hover,
        border_width=1,
        border_color=border,
        text_color=text_color,
        text_color_disabled=Colors.TEXT_DIM,
        height=height,
        corner_radius=Dims.CTRL_RADIUS,
        font=font(Fonts.SIZE_SM),
        **kwargs,
    )


def make_status_dot(parent, online: bool = False) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text="●",
        width=12,
        font=font(Fonts.SIZE_SM),
        text_color=Colors.GREEN if online else Colors.TEXT_DIM,
    )


def make_icon_tile(parent, glyph: str, colors: tuple, size: int = 30) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=glyph,
        width=size,
        height=size,
        corner_radius=7,
        fg_color=colors[0],
        text_color=colors[1],
        font=font(Fonts.SIZE_MD, "bold"),
    )


def bind_click(widget, command, hover_target=None, normal=None, hover=None):
    def on_enter(_):
        if hover_target is not None and hover:
            hover_target.configure(fg_color=hover)

    def on_leave(_):
        if hover_target is not None and normal:
            hover_target.configure(fg_color=normal)

    def attach(w):
        w.bind("<Button-1>", lambda e: command())
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)
        w.configure(cursor="hand2")
        for child in w.winfo_children():
            attach(child)

    attach(widget)


def make_search_field(parent, placeholder: str) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        height=32,
        corner_radius=Dims.CTRL_RADIUS,
        fg_color=Colors.PANEL_DEEP,
        border_color=Colors.LINE_STRONG,
        text_color=Colors.TEXT,
        placeholder_text_color=Colors.TEXT_DIM,
        font=font(Fonts.SIZE_SM),
    )
