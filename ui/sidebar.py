import customtkinter as ctk
from ui.theme import Colors, Fonts, Dims
from ui.widgets import font, make_eyebrow, make_status_dot, make_icon_tile

NAV_ITEMS = [
    ("dashboard", "Dashboard", "▦"),
    ("apps",      "Aplicaciones", "▤"),
    ("remote",    "Control remoto", "◈"),
]


class Sidebar(ctk.CTkFrame):

    def __init__(self, parent, on_connect, on_device_change, on_navigate, on_open_shell):
        super().__init__(
            parent,
            corner_radius=0,
            fg_color=Colors.SIDEBAR,
            width=Dims.SIDEBAR_W,
            border_width=0,
        )
        self.grid_propagate(False)
        self._on_connect       = on_connect
        self._on_device_change = on_device_change
        self._on_navigate      = on_navigate
        self._on_open_shell    = on_open_shell

        self._device_map: dict[str, str] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, padx=21, pady=(22, 22), sticky="ew")
        make_icon_tile(brand, "▮", ("#31537f", "#dceafe"), size=30).grid(row=0, column=0, rowspan=2, padx=(0, 10))
        ctk.CTkLabel(brand, text="ADB Control", font=font(Fonts.SIZE_MD, "bold"), text_color=Colors.TEXT, anchor="w").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(brand, text="DEVICE MANAGER", font=font(7), text_color=Colors.TEXT_DIM, anchor="w").grid(row=1, column=1, sticky="w")

        card = ctk.CTkFrame(
            self,
            fg_color="#112034",
            border_width=1,
            border_color="#28405b",
            corner_radius=9,
        )
        card.grid(row=1, column=0, padx=14, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.grid(row=0, column=0, padx=11, pady=(13, 0), sticky="ew")
        heading.grid_columnconfigure(1, weight=1)
        self.status_dot = make_status_dot(heading)
        self.status_dot.grid(row=0, column=0)
        self.status_label = ctk.CTkLabel(heading, text="Sin conexión", font=font(Fonts.SIZE_SM), text_color="#b9c9dc", anchor="w")
        self.status_label.grid(row=0, column=1, padx=(6, 0), sticky="w")
        ctk.CTkLabel(
            heading, text="ADB", font=font(Fonts.SIZE_XS, "bold"), text_color=Colors.BLUE_BRIGHT,
            fg_color="#213b5d", corner_radius=4, width=30, height=18,
        ).grid(row=0, column=2)

        mini = ctk.CTkFrame(card, fg_color="transparent")
        mini.grid(row=1, column=0, padx=11, pady=(14, 8), sticky="ew")
        mini.grid_columnconfigure(1, weight=1)
        make_icon_tile(mini, "▯", ("#253e60", "#7fb0ee"), size=34).grid(row=0, column=0, rowspan=2, padx=(0, 9))
        self.device_name = ctk.CTkLabel(mini, text="Sin dispositivo", font=font(Fonts.SIZE_BASE, "bold"), text_color=Colors.TEXT, anchor="w")
        self.device_name.grid(row=0, column=1, sticky="w")
        self.device_addr = ctk.CTkLabel(mini, text="—", font=font(Fonts.SIZE_XS), text_color="#718398", anchor="w")
        self.device_addr.grid(row=1, column=1, sticky="w")

        self.combo_dev = ctk.CTkComboBox(
            card,
            state="readonly",
            command=self._on_device_change,
            height=30,
            corner_radius=Dims.CTRL_RADIUS,
            fg_color=Colors.PANEL_DEEP,
            border_color=Colors.LINE_STRONG,
            button_color=Colors.SECONDARY_HOVER,
            button_hover_color=Colors.LINE_STRONG,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_hover_color=Colors.ROW_HOVER,
            text_color=Colors.TEXT_SOFT,
            font=font(Fonts.SIZE_XS),
            dropdown_font=font(Fonts.SIZE_XS),
        )
        self.combo_dev.grid(row=2, column=0, padx=11, pady=(0, 6), sticky="ew")

        self.entry_connect = ctk.CTkEntry(
            card,
            placeholder_text="IP del dispositivo y Enter",
            height=30,
            corner_radius=Dims.CTRL_RADIUS,
            fg_color=Colors.PANEL_DEEP,
            border_color=Colors.LINE_STRONG,
            text_color=Colors.TEXT,
            placeholder_text_color=Colors.TEXT_DIM,
            font=font(Fonts.SIZE_XS, mono=True),
        )
        self.entry_connect.grid(row=3, column=0, padx=11, pady=(0, 11), sticky="ew")
        self.entry_connect.bind("<Return>", self._submit)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=2, column=0, padx=14, pady=(28, 0), sticky="ew")
        nav.grid_columnconfigure(0, weight=1)
        make_eyebrow(nav, "Gestión").grid(row=0, column=0, padx=11, pady=(0, 9), sticky="w")
        for idx, (view_id, label, glyph) in enumerate(NAV_ITEMS, start=1):
            btn = ctk.CTkButton(
                nav,
                text=f"{glyph}   {label}",
                anchor="w",
                height=38,
                corner_radius=Dims.CTRL_RADIUS,
                fg_color="transparent",
                hover_color=Colors.NAV_HOVER,
                text_color=Colors.TEXT_MUTED,
                font=font(Fonts.SIZE_BASE),
                command=lambda v=view_id: self._on_navigate(v),
            )
            btn.grid(row=idx, column=0, pady=2, sticky="ew")
            self._nav_buttons[view_id] = btn

        self.apps_count = ctk.CTkLabel(
            self._nav_buttons["apps"],
            text="",
            font=font(Fonts.SIZE_XS, "bold"),
            text_color="#a9ccf5",
            fg_color="#2c4d79",
            corner_radius=9,
            height=18,
        )

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=14, pady=(0, 16), sticky="sew")
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(bottom, height=1, fg_color="#1a2a3b").grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkButton(
            bottom,
            text="▣   Terminal ADB",
            anchor="w",
            height=38,
            corner_radius=Dims.CTRL_RADIUS,
            fg_color="transparent",
            hover_color=Colors.NAV_HOVER,
            text_color=Colors.TEXT_MUTED,
            font=font(Fonts.SIZE_BASE),
            command=self._on_open_shell,
        ).grid(row=1, column=0, sticky="ew")

        footer = ctk.CTkFrame(bottom, fg_color="transparent")
        footer.grid(row=2, column=0, padx=8, pady=(12, 0), sticky="ew")
        make_status_dot(footer, online=True).pack(side="left")
        ctk.CTkLabel(footer, text="ADB daemon activo", font=font(Fonts.SIZE_XS), text_color="#6d8094").pack(side="left", padx=(6, 0))

        self.set_active_view("dashboard")

    def _submit(self, _event=None):
        text = self.entry_connect.get().strip()
        if text:
            self._on_connect(text)
            self.entry_connect.delete(0, "end")

    def set_active_view(self, view_id: str):
        for key, btn in self._nav_buttons.items():
            active = key == view_id
            btn.configure(
                fg_color=Colors.NAV_ACTIVE if active else "transparent",
                text_color=Colors.NAV_ACTIVE_TX if active else Colors.TEXT_MUTED,
            )

    def set_apps_count(self, count: int):
        if count:
            self.apps_count.configure(text=f" {count} ")
            self.apps_count.place(relx=1.0, x=-10, rely=0.5, anchor="e")
        else:
            self.apps_count.place_forget()

    def update_device_list(self, device_map: dict[str, str], preferred_label: str = ""):
        self._device_map = device_map
        labels = list(device_map.keys())
        self.combo_dev.configure(values=labels)
        if labels:
            self.combo_dev.set(preferred_label if preferred_label in labels else labels[0])
        else:
            self.combo_dev.set("")

    def set_status(self, text: str, ok: bool):
        self.status_label.configure(text=text)
        self.status_dot.configure(text_color=Colors.GREEN if ok else Colors.TEXT_DIM)

    def set_device_summary(self, name: str, address: str):
        self.device_name.configure(text=name or "Sin dispositivo")
        self.device_addr.configure(text=address or "—")

    def get_selected_device_id(self) -> str | None:
        return self._device_map.get(self.combo_dev.get())
