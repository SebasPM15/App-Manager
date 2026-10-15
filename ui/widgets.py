import tkinter as tk
import customtkinter as ctk
from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

from ui.theme import Colors, Fonts, Dims
from ui.icons import icon

_CTK_ONLY_LABEL_KEYS = ("width", "height", "corner_radius", "image", "compound")


def font(size: int = Fonts.SIZE_BASE, weight: str = "normal", mono: bool = False) -> ctk.CTkFont:
    family = Fonts.FAMILY_MONO if mono else Fonts.FAMILY_PRIMARY
    return ctk.CTkFont(family=family, size=size, weight=weight)


def _resolve_bg(master) -> str:
    widget = master
    while widget is not None:
        if isinstance(widget, ctk.CTk):
            color = widget.cget("fg_color")
        elif isinstance(widget, ctk.CTkBaseClass):
            color = widget.cget("fg_color")
        else:
            return widget.cget("bg")
        if isinstance(color, (tuple, list)):
            color = color[-1]
        if color and color != "transparent":
            return color
        widget = widget.master
    return Colors.BG


def _scale(master) -> float:
    try:
        return ScalingTracker.get_widget_scaling(master)
    except Exception:
        return 1.0


def _tk_font(spec, scale: float):
    if isinstance(spec, ctk.CTkFont):
        family, size, weight = spec.cget("family"), spec.cget("size"), spec.cget("weight")
        return (family, -abs(round(size * scale)), weight)
    return spec


class _PlainLabel(tk.Label):

    def __init__(self, master, text: str = "", font=None, text_color=None, fg_color=None,
                 anchor: str = "center", justify: str = "left", wraplength: int = 0, **_ignored):
        self._scale_factor = _scale(master)
        background = _resolve_bg(master) if fg_color in (None, "transparent") else fg_color
        super().__init__(
            master,
            text=text,
            font=_tk_font(font, self._scale_factor),
            fg=text_color or Colors.TEXT,
            bg=background,
            anchor=anchor,
            justify=justify,
            wraplength=round(wraplength * self._scale_factor),
            padx=0,
            pady=0,
            borderwidth=0,
            highlightthickness=0,
        )

    def configure(self, cnf=None, **kw):
        if "text_color" in kw:
            kw["fg"] = kw.pop("text_color")
        if "fg_color" in kw:
            color = kw.pop("fg_color")
            kw["bg"] = _resolve_bg(self.master) if color == "transparent" else color
        if "font" in kw:
            kw["font"] = _tk_font(kw["font"], self._scale_factor)
        if "wraplength" in kw:
            kw["wraplength"] = round(kw["wraplength"] * self._scale_factor)
        kw.pop("text_color_disabled", None)
        return super().configure(cnf, **kw)

    config = configure


class Box(tk.Frame):

    def __init__(self, master, fg_color=None, width: int = 0, height: int = 0, corner_radius=None,
                 border_width: int = 0, border_color=None, **_ignored):
        background = _resolve_bg(master) if fg_color in (None, "transparent") else fg_color
        super().__init__(
            master,
            bg=background,
            width=width,
            height=height,
            highlightthickness=border_width,
            highlightbackground=border_color or background,
            borderwidth=0,
        )

    def configure(self, cnf=None, **kw):
        if "fg_color" in kw:
            color = kw.pop("fg_color")
            kw["bg"] = _resolve_bg(self.master) if color == "transparent" else color
        kw.pop("corner_radius", None)
        return super().configure(cnf, **kw)

    config = configure


def Label(master, **kw):
    if any(key in kw for key in _CTK_ONLY_LABEL_KEYS):
        return ctk.CTkLabel(master, **kw)
    return _PlainLabel(master, **kw)


def make_panel(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=Colors.PANEL,
        border_width=1,
        border_color=Colors.LINE,
        corner_radius=Dims.PANEL_RADIUS,
        **kwargs,
    )


def make_eyebrow(parent, text: str, **kwargs):
    return Label(
        parent,
        text=text.upper(),
        font=font(Fonts.SIZE_XS, "bold"),
        text_color=Colors.TEXT_DIM,
        anchor="w",
        **kwargs,
    )


def make_button(parent, text: str, command, kind: str = "secondary", height: int = Dims.BTN_HEIGHT,
                icon_name: str | None = None, **kwargs) -> ctk.CTkButton:
    styles = {
        "primary":   (Colors.PRIMARY, Colors.PRIMARY_HOVER, "#6699dc", "#ffffff"),
        "secondary": (Colors.SECONDARY, Colors.SECONDARY_HOVER, Colors.LINE, "#b7c6d7"),
        "danger":    (Colors.DANGER_BG, Colors.DANGER_HOVER, Colors.DANGER_LINE, Colors.DANGER_TEXT),
        "ghost":     ("transparent", Colors.SURFACE, Colors.LINE, Colors.TEXT_MUTED),
    }
    fg, hover, border, text_color = styles[kind]
    if icon_name:
        kwargs["image"] = icon(icon_name, 15, text_color)
        kwargs["compound"] = "left"
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


def make_status_dot(parent, online: bool = False):
    return Label(
        parent,
        text="●",
        font=font(Fonts.SIZE_SM),
        text_color=Colors.GREEN if online else Colors.TEXT_DIM,
    )


def make_icon_tile(parent, icon_name: str, colors: tuple, size: int = 30, fg_color: str | None = None) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text="",
        image=icon(icon_name, round(size * 0.56), colors[1]),
        width=size,
        height=size,
        corner_radius=7,
        fg_color=colors[0],
    )


def bind_click(widget, command, hover_target=None, normal=None, hover=None):
    def on_enter(_):
        if hover_target is not None and hover:
            hover_target.configure(fg_color=hover)

    def on_leave(_):
        if hover_target is not None and normal:
            hover_target.configure(fg_color=normal)

    def attach(w):
        w.bind("<Button-1>", lambda e: command(), add="+")
        w.bind("<Enter>", on_enter, add="+")
        w.bind("<Leave>", on_leave, add="+")
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
