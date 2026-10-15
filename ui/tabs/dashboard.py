import customtkinter as ctk
from ui.theme import Colors, Fonts, Dims
from ui.icons import icon
from ui.widgets import Label, Box, font, make_panel, make_eyebrow, make_status_dot, make_icon_tile, bind_click, place_scaled

QUICK_ACTIONS = [
    ("scrcpy",     "Abrir Scrcpy",        "Iniciar espejo de pantalla", "play", Colors.ICON_VIOLET),
    ("screenshot", "Tomar captura",       "Guardar pantalla actual",    "camera", Colors.ICON_BLUE),
    ("sync_time",  "Sincronizar hora",    "Ajustar fecha y hora",       "clock", Colors.ICON_AMBER),
    ("reboot",     "Reiniciar",           "Reiniciar dispositivo",      "power", Colors.ICON_RED),
]

DETAIL_FIELDS = [
    ("model",    "Modelo"),
    ("brand",    "Fabricante"),
    ("android",  "Android"),
    ("serial",   "Identificador"),
    ("conn",     "Conexión"),
    ("ip",       "IP local"),
]


class DashboardTab(ctk.CTkFrame):

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, fg_color="transparent")
        self._cb = callbacks
        self._values: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=3, uniform="dash")
        self.grid_columnconfigure(1, weight=2, uniform="dash")
        self.grid_rowconfigure(0, weight=1)

        main = Box(self, fg_color="transparent")
        main.grid(row=0, column=0, padx=(0, 11), sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        overview = make_panel(main)
        overview.grid(row=0, column=0, sticky="ew")
        overview.grid_columnconfigure(0, weight=1)

        head = Box(overview, fg_color="transparent")
        head.grid(row=0, column=0, padx=20, pady=(18, 0), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        title = Box(head, fg_color="transparent")
        title.grid(row=0, column=0, sticky="w")
        make_eyebrow(title, "Información del dispositivo").pack(anchor="w")
        self.lbl_title = Label(title, text="Sin dispositivo", font=font(Fonts.SIZE_LG, "bold"), text_color=Colors.TEXT, anchor="w")
        self.lbl_title.pack(anchor="w", pady=(5, 0))

        pill = ctk.CTkFrame(head, fg_color=Colors.GREEN_DIM, corner_radius=5)
        pill.grid(row=0, column=1, sticky="ne")
        self.pill_dot = make_status_dot(pill)
        self.pill_dot.configure(fg_color="transparent")
        self.pill_dot.pack(side="left", padx=(8, 0), pady=4)
        self.pill_text = Label(pill, text="Desconectado", font=font(Fonts.SIZE_XS), text_color="#79d0a4")
        self.pill_text.pack(side="left", padx=(4, 8))

        details = Box(overview, fg_color="transparent")
        details.grid(row=1, column=0, padx=20, pady=(24, 22), sticky="ew")
        details.grid_columnconfigure(0, weight=0)
        details.grid_columnconfigure(1, weight=1)

        visual = ctk.CTkFrame(
            details, width=105, height=114, fg_color="#12263c",
            border_width=1, border_color="#304961", corner_radius=17,
        )
        visual.grid(row=0, column=0, padx=(0, 28), sticky="n")
        visual.grid_propagate(False)
        visual.grid_columnconfigure(0, weight=1)
        visual.grid_rowconfigure((0, 3), weight=1)
        Label(visual, text="", image=icon("smartphone", 44, "#7ea8dd"), width=48, height=48).grid(row=1, column=0, pady=(14, 0))
        self.lbl_visual = Label(visual, text="Android", font=font(Fonts.SIZE_XS), text_color="#8297af")
        self.lbl_visual.grid(row=2, column=0, pady=(0, 14))

        grid = Box(details, fg_color="transparent")
        grid.grid(row=0, column=1, sticky="ew")
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="fields")
        for idx, (key, label) in enumerate(DETAIL_FIELDS):
            cell = Box(grid, fg_color="transparent")
            cell.grid(row=idx // 3, column=idx % 3, sticky="nw", pady=(0, 18))
            Label(cell, text=label, font=font(Fonts.SIZE_XS), text_color="#718399", anchor="w").pack(anchor="w")
            value = Label(cell, text="—", font=font(Fonts.SIZE_SM), text_color=Colors.TEXT_SOFT, anchor="w", wraplength=130, justify="left")
            value.pack(anchor="w", pady=(4, 0))
            self._values[key] = value

        heading = Box(main, fg_color="transparent")
        heading.grid(row=1, column=0, pady=(24, 12), sticky="ew")
        Label(heading, text="Acciones rápidas", font=font(Fonts.SIZE_MD, "bold"), text_color=Colors.TEXT, anchor="w").pack(anchor="w")
        Label(heading, text="Operaciones frecuentes sobre el dispositivo.", font=font(Fonts.SIZE_XS), text_color="#8191a5", anchor="w").pack(anchor="w", pady=(4, 0))

        quick = Box(main, fg_color="transparent")
        quick.grid(row=2, column=0, sticky="ew")
        quick.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="quick")
        for col, (key, title_text, subtitle, icon_name, colors) in enumerate(QUICK_ACTIONS):
            card = ctk.CTkFrame(quick, fg_color=Colors.CARD, border_width=1, border_color="#23384e", corner_radius=8, height=112)
            card.grid(row=0, column=col, padx=(0 if col == 0 else 4, 0 if col == 3 else 4), sticky="nsew")
            card.grid_propagate(False)
            place_scaled(make_icon_tile(card, icon_name, colors, size=29), 14, 14)
            place_scaled(Label(card, text=title_text, font=font(Fonts.SIZE_SM, "bold"), text_color=Colors.TEXT, anchor="w"), 14, 56)
            place_scaled(Label(card, text=subtitle, font=font(Fonts.SIZE_XS), text_color="#778ba1", anchor="w", wraplength=120, justify="left"), 14, 80)
            bind_click(card, self._cb.get(key, lambda: None), hover_target=card, normal=Colors.CARD, hover=Colors.CARD_HOVER)

        foreground = make_panel(main)
        foreground.grid(row=3, column=0, pady=(21, 0), sticky="ew")
        foreground.grid_columnconfigure(0, weight=1)
        fg_copy = Box(foreground, fg_color="transparent")
        fg_copy.grid(row=0, column=0, padx=17, pady=14, sticky="w")
        make_eyebrow(fg_copy, "Aplicación en primer plano").pack(anchor="w")
        self.lbl_foreground = Label(fg_copy, text="—", font=font(Fonts.SIZE_BASE), text_color=Colors.TEXT, anchor="w")
        self.lbl_foreground.pack(anchor="w", pady=(8, 0))

        side = Box(self, fg_color="transparent")
        side.grid(row=0, column=1, padx=(11, 0), sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        heading = Box(side, fg_color="transparent")
        heading.grid(row=0, column=0, pady=(0, 12), sticky="ew")
        Label(heading, text="Estado del sistema", font=font(Fonts.SIZE_MD, "bold"), text_color=Colors.TEXT, anchor="w").pack(anchor="w")
        Label(heading, text="Datos del dispositivo seleccionado.", font=font(Fonts.SIZE_XS), text_color="#8191a5", anchor="w").pack(anchor="w", pady=(4, 0))

        self.stat_battery = self._stat_card(side, 1, "BATERÍA", "battery", Colors.ICON_GREEN)
        self.stat_temp = self._stat_card(side, 2, "TEMPERATURA", "gauge", Colors.ICON_AMBER)

        network = make_panel(side)
        network.grid(row=3, column=0, pady=(20, 0), sticky="ew")
        top = Box(network, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 0))
        make_eyebrow(top, "Conexión activa").pack(side="left")
        self.lbl_net_title = Label(network, text="—", font=font(Fonts.SIZE_BASE, "bold"), text_color=Colors.TEXT, anchor="w")
        self.lbl_net_title.pack(anchor="w", padx=14, pady=(11, 0))
        self.lbl_net_addr = Label(network, text="", font=font(Fonts.SIZE_XS), text_color="#718499", anchor="w")
        self.lbl_net_addr.pack(anchor="w", padx=14, pady=(8, 14))

    def _stat_card(self, parent, row: int, label: str, icon_name: str, colors: tuple) -> dict:
        card = ctk.CTkFrame(parent, fg_color="#132235", border_width=1, border_color="#24384e", corner_radius=8)
        card.grid(row=row, column=0, pady=(0, 9), sticky="ew")
        make_icon_tile(card, icon_name, colors, size=34).grid(row=0, column=0, rowspan=3, padx=14, pady=14)
        make_eyebrow(card, label).grid(row=0, column=1, sticky="sw", pady=(12, 0))
        value = Label(card, text="—", font=font(Fonts.SIZE_XL, "bold"), text_color=Colors.TEXT, anchor="w")
        value.grid(row=1, column=1, sticky="w")
        detail = Label(card, text="", font=font(Fonts.SIZE_XS), text_color="#7890a5", anchor="w")
        detail.grid(row=2, column=1, sticky="nw", pady=(0, 12))
        return {"value": value, "detail": detail}

    def update(self, details: dict, device_id: str = ""):
        conn = details.get("connection_type", "USB")
        model = details.get("model", "—")
        android = details.get("android_ver", "—")
        self.lbl_title.configure(text=model)
        self.pill_text.configure(text="Conectado")
        self.pill_dot.configure(text_color=Colors.GREEN)
        self.lbl_visual.configure(text=f"Android {android}")

        self._values["model"].configure(text=details.get("model_name") or model)
        self._values["brand"].configure(text=details.get("brand", "—"))
        self._values["android"].configure(text=f"{android} (API {details.get('sdk_ver', '—')})")
        self._values["serial"].configure(text=device_id or "—")
        self._values["conn"].configure(text="Wi-Fi ADB" if conn == "WiFi" else "USB")
        self._values["ip"].configure(text=details.get("ip", "—"))
        self.lbl_foreground.configure(text=details.get("foreground_app", "—"))

        pct = details.get("battery_level", 0)
        self.stat_battery["value"].configure(text=f"{pct}%", text_color=Colors.battery_color(pct))
        self.stat_battery["detail"].configure(text=details.get("battery_status", "—"))
        self.stat_temp["value"].configure(text=details.get("battery_temp", "—"))
        self.stat_temp["detail"].configure(text="Temperatura de la batería")

        self.lbl_net_title.configure(text="Wi-Fi ADB" if conn == "WiFi" else "USB")
        self.lbl_net_addr.configure(text=f"IP {details.get('ip', '—')}")

    def clear(self):
        self.lbl_title.configure(text="Sin dispositivo")
        self.pill_text.configure(text="Desconectado")
        self.pill_dot.configure(text_color=Colors.TEXT_DIM)
        self.lbl_visual.configure(text="Android")
        for lbl in self._values.values():
            lbl.configure(text="—")
        self.lbl_foreground.configure(text="—")
        for stat in (self.stat_battery, self.stat_temp):
            stat["value"].configure(text="—", text_color=Colors.TEXT)
            stat["detail"].configure(text="")
        self.lbl_net_title.configure(text="—")
        self.lbl_net_addr.configure(text="")
