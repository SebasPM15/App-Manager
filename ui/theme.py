import sys

IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"


class Colors:
    BG            = "#0a111c"
    SIDEBAR       = "#0c1623"
    SURFACE       = "#111c2a"
    PANEL         = "#132030"
    PANEL_DEEP    = "#0e1b2a"
    CARD          = "#142335"
    CARD_HOVER    = "#1b3048"
    ROW_HOVER     = "#172b43"
    CONSOLE       = "#0c1725"

    LINE          = "#23364b"
    LINE_SOFT     = "#1d2c3f"
    LINE_STRONG   = "#2a3e54"

    TEXT          = "#e7edf6"
    TEXT_SOFT     = "#d2deeb"
    TEXT_MUTED    = "#8796a9"
    TEXT_DIM      = "#65788d"

    BLUE          = "#6c9de7"
    BLUE_BRIGHT   = "#72a5e6"
    BLUE_DIM      = "#203653"
    GREEN         = "#5ed59e"
    GREEN_DIM     = "#18372f"
    AMBER         = "#e8b267"
    RED           = "#dc747c"
    VIOLET        = "#a28ee8"

    NAV_ACTIVE    = "#1c3555"
    NAV_ACTIVE_TX = "#dbeaff"
    NAV_HOVER     = "#142436"

    PRIMARY       = "#4779bd"
    PRIMARY_HOVER = "#5689cd"
    SECONDARY     = "#172638"
    SECONDARY_HOVER = "#21344a"
    DANGER_BG     = "#2a1d26"
    DANGER_HOVER  = "#41232c"
    DANGER_LINE   = "#56333b"
    DANGER_TEXT   = "#e69198"

    ICON_VIOLET   = ("#30294f", "#b1a1e9")
    ICON_BLUE     = ("#1e3a5b", "#76abe9")
    ICON_AMBER    = ("#4a3927", "#e3b76e")
    ICON_RED      = ("#452a35", "#de7d88")
    ICON_GREEN    = ("#183a34", "#5ed59e")

    @staticmethod
    def battery_color(pct: int) -> str:
        if pct < 20:
            return Colors.RED
        if pct < 50:
            return Colors.AMBER
        return Colors.GREEN


class Fonts:
    FAMILY_PRIMARY = "Arial"
    FAMILY_MONO    = "Consolas" if IS_WINDOWS else ("Menlo" if IS_MACOS else "DejaVu Sans Mono")

    SIZE_XS   = 9
    SIZE_SM   = 10
    SIZE_BASE = 11
    SIZE_MD   = 12
    SIZE_LG   = 14
    SIZE_XL   = 18
    SIZE_2XL  = 22


class Dims:
    SIDEBAR_W      = 240
    TOPBAR_H       = 54
    CONSOLE_H      = 200
    CONSOLE_H_BAR  = 43
    PANEL_RADIUS   = 10
    CTRL_RADIUS    = 6
    BTN_HEIGHT     = 33
    PAD            = 14
    PAD_LG         = 28
