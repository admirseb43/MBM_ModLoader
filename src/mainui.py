"""MBM Mod Loader - a mod loader for Monster Black Market.

Entry point. Built incrementally; this step lays out the main window shell.
"""

import tkinter as tk
from pathlib import Path
import webbrowser
from tkinter import filedialog, font as tkfont, ttk

from assets import load_svg_as_photo
import lang
from installed_mod import InstalledMod
from mod_database import ModDatabase
from logger import setup_logger, write_separator
from profile import Profile, create_profile, list_profiles, load_profile, toggle_favorite
from version import APP_VERSION

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 960

# Dark theme palette
COLOR_BG = "#1e1e1e"          # main background
COLOR_BAR = "#252526"         # top/bottom bars
COLOR_WIDGET = "#333333"      # interactive widgets (dropdowns, etc.)
COLOR_WIDGET_ACTIVE = "#3c3c3c"  # hovered/active widget state
COLOR_BORDER = "#3c3c3c"      # subtle separators
COLOR_TEXT = "#e0e0e0"        # primary text
COLOR_TEXT_DIM = "#888888"    # secondary text (version, etc.)
COLOR_WARN = "#ff5555"        # warnings / errors (bright)
COLOR_WARN_DIM = "#8a3a3a"    # dim end of the warning pulse (still readable)
COLOR_GOLD = "#e5c07b"        # mod author name
COLOR_LINK = "#569cd6"        # clickable repository link
COLOR_OK = "#4ec994"          # up to date
COLOR_UPDATE = "#e5a550"      # update available

# (checkbox, name, author, newest version, local version) — must match between header and rows
_MOD_COL_WIDTHS = (40, 260, 180, 180, 120)

STAR_FILLED = "★"        # ★
STAR_EMPTY = "☆"         # ☆

# Maps language key → flag SVG filename (lipis/flag-icons, 4x3 folder).
_LANG_FLAGS = {"eng": "gb.svg", "fr": "fr.svg", "ch": "cn.svg", "ru": "ru.svg"}


def _color_gradient(start_hex: str, end_hex: str, steps: int) -> list:
    """Return a list of `steps` hex colors interpolating start -> end."""
    s = tuple(int(start_hex[i:i + 2], 16) for i in (1, 3, 5))
    e = tuple(int(end_hex[i:i + 2], 16) for i in (1, 3, 5))
    colors = []
    for n in range(steps):
        t = n / (steps - 1) if steps > 1 else 0
        rgb = tuple(round(s[c] + (e[c] - s[c]) * t) for c in range(3))
        colors.append("#%02x%02x%02x" % rgb)
    return colors


class ModLoaderApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.log = setup_logger()
        self.log.info("Application started")
        self._current_lang = "eng"
        lang.load(self._current_lang)
        self.profile = load_profile(self.log)

        self.title(lang.t("app.title"))
        self.configure(bg=COLOR_BG)
        self._center_window(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.resizable(False, False)
        self._setup_style()
        self._apply_anim_job = None

        self._build_top_bar()
        self._build_content()
        self._build_bottom_bar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._open_repo_check)

    def _on_close(self) -> None:
        """Log shutdown then close the window."""
        if self._blink_job is not None:
            self.after_cancel(self._blink_job)
            self._blink_job = None
        if self._apply_anim_job is not None:
            self.after_cancel(self._apply_anim_job)
            self._apply_anim_job = None
        self.log.info("Application closed")
        write_separator(self.log)
        self.destroy()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=COLOR_WIDGET,
            troughcolor=COLOR_BAR,
            bordercolor=COLOR_BG,
            arrowcolor=COLOR_TEXT_DIM,
            relief="flat",
            arrowsize=12,
        )
        style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", COLOR_WIDGET_ACTIVE), ("pressed", COLOR_WIDGET_ACTIVE)],
        )

    def _center_window(self, width: int, height: int) -> None:
        """Size the window and center it on screen."""
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_top_bar(self) -> None:
        """Top bar: application menus. Far right holds the profile selector."""
        top_bar = tk.Frame(self, bg=COLOR_BAR, height=40,
                           highlightbackground=COLOR_BORDER, highlightthickness=1)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)
        self.top_bar = top_bar

        self._build_menu_button()

        # Profile selector, anchored to the far right: "Profile" label + dropdown.
        self.profile_var = tk.StringVar(value=self.profile.name)
        self.profile_popup = None  # open Toplevel, or None when closed

        self.profile_button = tk.Button(
            top_bar, command=self._toggle_profile_popup,
            bg=COLOR_WIDGET, fg=COLOR_TEXT,
            activebackground=COLOR_WIDGET_ACTIVE, activeforeground=COLOR_TEXT,
            relief="flat", bd=0, font=("Segoe UI", 10), width=16, anchor="w",
            padx=8, compound="left",
        )
        self.profile_button.pack(side="right", padx=(6, 10))

        profile_label = tk.Label(top_bar, text=lang.t("top_bar.profile_label"), bg=COLOR_BAR,
                                fg=COLOR_TEXT, font=("Segoe UI", 10))
        profile_label.pack(side="right")

        self._update_profile_button()
        self._build_path_warning()

    def _build_menu_button(self) -> None:
        """Left-side 'Menu' button that opens a dropdown."""
        self.menu_popup = None
        self.menu_button = tk.Button(
            self.top_bar, text=lang.t("top_bar.menu"),
            command=self._toggle_menu_popup,
            bg=COLOR_BAR, fg=COLOR_TEXT,
            activebackground=COLOR_WIDGET, activeforeground=COLOR_TEXT,
            relief="flat", bd=0, font=("Segoe UI", 10), padx=10,
        )
        self.menu_button.pack(side="left", padx=(6, 0))

    def _toggle_menu_popup(self) -> None:
        if self.menu_popup is not None:
            self._close_menu_popup()
        else:
            self._open_menu_popup()

    def _close_menu_popup(self) -> None:
        if self.menu_popup is not None:
            self.menu_popup.destroy()
            self.menu_popup = None

    def _open_menu_popup(self) -> None:
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=COLOR_BORDER)
        self.menu_popup = popup

        self.menu_button.update_idletasks()
        x = self.menu_button.winfo_rootx()
        y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
        popup.geometry(f"+{x}+{y}")

        inner = tk.Frame(popup, bg=COLOR_WIDGET)
        inner.pack(padx=1, pady=1)

        def _menu_item(text: str, command):
            lbl = tk.Label(
                inner, text=text, bg=COLOR_WIDGET, fg=COLOR_TEXT,
                font=("Segoe UI", 10), anchor="w", padx=12, pady=6, cursor="hand2",
                width=18,
            )
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda _e: command())
            lbl.bind("<Enter>", lambda _e: lbl.configure(bg=COLOR_WIDGET_ACTIVE))
            lbl.bind("<Leave>", lambda _e: lbl.configure(bg=COLOR_WIDGET))

        _menu_item(lang.t("menu.set_game_folder"), self._on_set_game_folder)

        tk.Frame(inner, bg=COLOR_BORDER, height=1).pack(fill="x")

        _menu_item(lang.t("menu.force_refresh"), self._on_force_refresh)

        popup.bind("<FocusOut>", lambda _e: self._close_menu_popup())
        popup.bind("<Escape>", lambda _e: self._close_menu_popup())
        popup.focus_set()

    def _on_force_refresh(self) -> None:
        self._close_menu_popup()
        self.log.info("Force refresh triggered by user")
        self._open_repo_check()

    def _on_set_game_folder(self) -> None:
        """Open a folder picker, validate it contains the game exe, then save."""
        self._close_menu_popup()
        path = filedialog.askdirectory(title=lang.t("folder_picker.title"))
        if not path:
            return
        if not (Path(path) / "MonsterBlackMarket.exe").is_file():
            self.log.error(
                f"Game folder validation failed: 'MonsterBlackMarket.exe' not found in '{path}'"
            )
            self._show_error_dialog(
                lang.t("errors.invalid_folder_title"),
                lang.t("errors.invalid_folder_message"),
            )
            return
        self.profile.game_folder_path = path
        self.profile.save()
        self.log.info(f"Game folder set: {path}")
        self._update_path_warning()

    def _show_error_dialog(self, title: str, message: str) -> None:
        """Generic themed error dialog with an OK button."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=COLOR_BG)
        dialog.resizable(False, False)
        dialog.transient(self)

        body = tk.Frame(dialog, bg=COLOR_BG, padx=20, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=message, bg=COLOR_BG, fg=COLOR_WARN,
                 font=("Segoe UI", 10), justify="left").pack(anchor="w")

        tk.Button(
            body, text=lang.t("buttons.ok"), command=dialog.destroy,
            bg=COLOR_WIDGET, fg=COLOR_TEXT, activebackground=COLOR_WIDGET_ACTIVE,
            activeforeground=COLOR_TEXT, relief="flat", bd=0,
            font=("Segoe UI", 10), padx=14, pady=4, cursor="hand2",
        ).pack(side="right", pady=(14, 0))

        dialog.bind("<Return>", lambda _e: dialog.destroy())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        self._center_dialog(dialog)
        dialog.grab_set()

    def _build_path_warning(self) -> None:
        """Centered, pulsing warning shown when the game folder path is unset."""
        self._blink_job = None
        # Ping-pong palette: bright -> dim -> bright. Text stays readable.
        steps = _color_gradient(COLOR_WARN, COLOR_WARN_DIM, 14)
        self._pulse_colors = steps + steps[-2:0:-1]
        self._pulse_index = 0
        self.path_warning = tk.Label(
            self.top_bar, text=lang.t("top_bar.path_warning"),
            bg=COLOR_BAR, fg=COLOR_WARN, font=("Segoe UI", 10, "bold"),
        )
        self._update_path_warning()

    def _update_path_warning(self) -> None:
        """Show/hide and (un)start the pulse based on the active profile."""
        needs_path = not (self.profile.game_folder_path or "").strip()
        if needs_path:
            self.path_warning.place(relx=0.5, rely=0.5, anchor="center")
            if self._blink_job is None:
                self._pulse()
        else:
            if self._blink_job is not None:
                self.after_cancel(self._blink_job)
                self._blink_job = None
            self.path_warning.place_forget()
        canvas = getattr(self, "_apply_canvas", None)
        if canvas is not None:
            enabled = getattr(self, "_apply_enabled", [False])
            enabled[0] = not needs_path
            if needs_path:
                self._stop_apply_anim()
            else:
                canvas.configure(cursor="hand2")
                text_id = getattr(self, "_apply_text_id", None)
                if text_id is not None:
                    canvas.itemconfig(text_id, fill=COLOR_TEXT)
                self._start_apply_anim()

    def _pulse(self) -> None:
        """Advance the warning color one step along the pulse, then reschedule."""
        color = self._pulse_colors[self._pulse_index]
        self.path_warning.configure(fg=color)
        self._pulse_index = (self._pulse_index + 1) % len(self._pulse_colors)
        self._blink_job = self.after(60, self._pulse)

    def _update_profile_button(self) -> None:
        """Show the selected profile on the button, prefixed with its star."""
        name = self.profile_var.get()
        is_fav = any(p.path.stem == name and p.favorite for p in list_profiles(self.log))
        star = STAR_FILLED if is_fav else STAR_EMPTY
        self.profile_button.configure(text=f"{star}  {name}", fg=COLOR_TEXT)

    def _toggle_profile_popup(self) -> None:
        """Open the profile dropdown, or close it if already open."""
        if self.profile_popup is not None:
            self._close_profile_popup()
        else:
            self._open_profile_popup()

    def _close_profile_popup(self) -> None:
        if self.profile_popup is not None:
            self.profile_popup.destroy()
            self.profile_popup = None

    def _open_profile_popup(self) -> None:
        """Build the borderless dropdown listing every valid profile."""
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=COLOR_BORDER)  # acts as a 1px border
        self.profile_popup = popup

        # Position just below the profile button, right-aligned to it.
        self.profile_button.update_idletasks()
        x = self.profile_button.winfo_rootx()
        y = self.profile_button.winfo_rooty() + self.profile_button.winfo_height()
        popup.geometry(f"+{x}+{y}")

        inner = tk.Frame(popup, bg=COLOR_WIDGET)
        inner.pack(padx=1, pady=1)

        for prof in list_profiles(self.log):
            self._build_profile_row(inner, prof)

        self._build_new_profile_row(inner)

        # Close when the popup loses focus (e.g. clicking elsewhere) or Escape.
        popup.bind("<FocusOut>", lambda _e: self._close_profile_popup())
        popup.bind("<Escape>", lambda _e: self._close_profile_popup())
        popup.focus_set()

    def _build_profile_row(self, parent: tk.Frame, prof) -> None:
        """One dropdown row: a clickable star plus the profile name."""
        name = prof.path.stem  # hide the .json extension
        row = tk.Frame(parent, bg=COLOR_WIDGET)
        row.pack(fill="x")

        star = tk.Label(
            row, text=STAR_FILLED if prof.favorite else STAR_EMPTY,
            bg=COLOR_WIDGET, fg=COLOR_TEXT,
            font=("Segoe UI", 11), padx=8, cursor="hand2",
        )
        star.pack(side="left")
        star.bind("<Button-1>", lambda _e, p=prof.path: self._on_star_clicked(p))

        name_label = tk.Label(
            row, text=name, bg=COLOR_WIDGET, fg=COLOR_TEXT,
            font=("Segoe UI", 10), anchor="w", padx=4, cursor="hand2", width=14,
        )
        name_label.pack(side="left", fill="x", expand=True)
        name_label.bind("<Button-1>", lambda _e, n=name: self._on_profile_selected(n))

        # Hover feedback on the name part.
        for w in (row, name_label):
            w.bind("<Enter>", lambda _e, lbl=name_label: lbl.configure(bg=COLOR_WIDGET_ACTIVE))
            w.bind("<Leave>", lambda _e, lbl=name_label: lbl.configure(bg=COLOR_WIDGET))

    def _on_star_clicked(self, path) -> None:
        """Toggle the favorite flag, then rebuild the popup to reflect it."""
        toggle_favorite(path, self.log)
        self._update_profile_button()  # button star may have changed
        # Rebuild the open popup so every star reflects the new state.
        self._close_profile_popup()
        self._open_profile_popup()

    def _on_profile_selected(self, name: str) -> None:
        """Handle the user picking a profile from the dropdown."""
        self.profile_var.set(name)
        self.log.info(f"Profile selected: {name}")
        self._update_profile_button()
        self._close_profile_popup()

    def _build_new_profile_row(self, parent: tk.Frame) -> None:
        """Last dropdown row: '+ new' to create a profile."""
        separator = tk.Frame(parent, bg=COLOR_BORDER, height=1)
        separator.pack(fill="x")

        row = tk.Label(
            parent, text=lang.t("profile_dropdown.new"), bg=COLOR_WIDGET, fg=COLOR_TEXT,
            font=("Segoe UI", 11, "bold"), anchor="w", padx=8, cursor="hand2",
        )
        row.pack(fill="x")
        row.bind("<Button-1>", lambda _e: self._on_new_profile())
        row.bind("<Enter>", lambda _e: row.configure(bg=COLOR_WIDGET_ACTIVE))
        row.bind("<Leave>", lambda _e: row.configure(bg=COLOR_WIDGET))

    def _on_new_profile(self) -> None:
        """Close the dropdown and open the new-profile dialog."""
        self._close_profile_popup()
        self._open_new_profile_dialog()

    def _open_new_profile_dialog(self) -> None:
        """Modal dialog to name and create a new profile (default content)."""
        dialog = tk.Toplevel(self)
        dialog.title(lang.t("new_profile_dialog.title"))
        dialog.configure(bg=COLOR_BG)
        dialog.resizable(False, False)
        dialog.transient(self)

        body = tk.Frame(dialog, bg=COLOR_BG, padx=20, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=lang.t("new_profile_dialog.name_label"), bg=COLOR_BG, fg=COLOR_TEXT,
                font=("Segoe UI", 10)).pack(anchor="w")

        name_entry = tk.Entry(body, bg=COLOR_WIDGET, fg=COLOR_TEXT,
                             insertbackground=COLOR_TEXT, relief="flat",
                             font=("Segoe UI", 11), width=28)
        name_entry.pack(fill="x", pady=(4, 2), ipady=4)
        name_entry.focus_set()

        info = tk.Label(body, text=lang.t("new_profile_dialog.hint"),
                       bg=COLOR_BG, fg=COLOR_TEXT_DIM, font=("Segoe UI", 8))
        info.pack(anchor="w")

        error = tk.Label(body, text="", bg=COLOR_BG, fg="#e06c75",
                        font=("Segoe UI", 8))
        error.pack(anchor="w", pady=(4, 0))

        def submit(_event=None):
            try:
                profile = create_profile(name_entry.get(), self.log)
            except (ValueError, FileExistsError) as exc:
                error.configure(text=str(exc))
                return
            dialog.destroy()
            self._on_profile_selected(profile.name)

        buttons = tk.Frame(body, bg=COLOR_BG)
        buttons.pack(fill="x", pady=(14, 0))

        cancel_btn = tk.Button(
            buttons, text=lang.t("buttons.cancel"), command=dialog.destroy,
            bg=COLOR_WIDGET, fg=COLOR_TEXT, activebackground=COLOR_WIDGET_ACTIVE,
            activeforeground=COLOR_TEXT, relief="flat", bd=0, font=("Segoe UI", 10),
            padx=14, pady=4, cursor="hand2",
        )
        cancel_btn.pack(side="right")

        create_btn = tk.Button(
            buttons, text=lang.t("buttons.create"), command=submit,
            bg=COLOR_WIDGET, fg=COLOR_TEXT, activebackground=COLOR_WIDGET_ACTIVE,
            activeforeground=COLOR_TEXT, relief="flat", bd=0, font=("Segoe UI", 10),
            padx=14, pady=4, cursor="hand2",
        )
        create_btn.pack(side="right", padx=(0, 8))

        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        self._center_dialog(dialog)
        dialog.grab_set()  # modal

    def _center_dialog(self, dialog: tk.Toplevel) -> None:
        """Center a dialog over the main window."""
        dialog.update_idletasks()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 3
        dialog.geometry(f"+{x}+{y}")

    def _open_repo_check(self) -> None:
        """Open a blocking loading window then check every mod repo in a background thread."""
        import threading
        from repo_checker import get_releases
        from file_checker import get_file_version

        self._mod_statuses = {}
        mods = ModDatabase.load().mods
        total = len(mods)
        game_folder = (self.profile.game_folder_path or "").strip()

        popup = tk.Toplevel(self)
        popup.title(lang.t("app.title"))
        popup.configure(bg=COLOR_BG)
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        body = tk.Frame(popup, bg=COLOR_BG, padx=40, pady=28)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Loading mod repositories",
                 bg=COLOR_BG, fg=COLOR_TEXT, font=("Segoe UI", 11, "bold")).pack(pady=(0, 12))

        counter_lbl = tk.Label(body, text=f"0 / {total}",
                               bg=COLOR_BG, fg=COLOR_TEXT_DIM, font=("Segoe UI", 10))
        counter_lbl.pack()

        self._center_dialog(popup)
        self._set_apply_waiting(True)
        self.log.info("Repos are loading")

        done = [0]

        def worker():
            for mod in mods:
                try:
                    versions = get_releases(mod.url_repo)
                    version_str = ", ".join(versions) if versions else "no releases found"
                    self.log.info(f"[{mod.name}] Releases: {version_str}")
                    file_version = None  # None = file absent
                    if game_folder and mod.file_name:
                        mod_file = Path(game_folder) / "mods" / mod.file_name
                        if mod_file.is_file():
                            fv = get_file_version(mod_file)
                            file_version = fv if fv is not None else ""  # "" = present but unreadable
                            if fv:
                                self.log.info(f"[{mod.name}] Local file version: {fv}")
                            else:
                                self.log.warning(f"[{mod.name}] Local file found but version unreadable")
                    self.after(0, lambda name=mod.name, v=versions, fv=file_version: self._set_mod_releases(name, v, fv))
                except Exception as exc:
                    self.log.error(f"[{mod.name}] Failed to reach '{mod.url_repo}': {exc}")
                    self.after(0, lambda name=mod.name: self._mark_mod_unavailable(name))
                done[0] += 1
                self.after(0, lambda n=done[0]: counter_lbl.configure(text=f"{n} / {total}"))
            self.after(0, _on_done)

        def _on_done():
            counter_lbl.configure(text="Loading complete!")
            self.log.info("Mods are loaded")
            self._set_apply_waiting(False)
            self._refresh_apply_state()
            self.after(1000, popup.destroy)

        threading.Thread(target=worker, daemon=True).start()

    def _build_content(self) -> None:
        """Middle content area — mod list."""
        content = tk.Frame(self, bg=COLOR_BG)
        content.pack(side="top", fill="both", expand=True)
        self.content = content
        self._mod_row_refs: dict[str, dict] = {}
        self._mod_statuses: dict[str, str] = {}
        self._initial_mod_names: set[str] = {m.name for m in self.profile.mods}

        db = ModDatabase.load()

        # Header row
        header = tk.Frame(content, bg=COLOR_BAR)
        header.pack(fill="x")
        for i, w in enumerate(_MOD_COL_WIDTHS):
            header.columnconfigure(i, minsize=w)
        col_texts = ["", lang.t("mod_list.col_name"), lang.t("mod_list.col_author"), lang.t("mod_list.col_newest"), lang.t("mod_list.col_local")]
        for i, text in enumerate(col_texts):
            if text:
                tk.Label(header, text=text, bg=COLOR_BAR, fg=COLOR_TEXT_DIM,
                         font=("Segoe UI", 9), anchor="w", padx=8, pady=6).grid(row=0, column=i, sticky="w")

        tk.Frame(content, bg=COLOR_BORDER, height=1).pack(fill="x")

        # Apply bar (packed before the canvas so it anchors to the bottom)
        apply_bar = tk.Frame(content, bg=COLOR_BAR, height=44,
                             highlightbackground=COLOR_BORDER, highlightthickness=1)
        apply_bar.pack(side="bottom", fill="x")
        apply_bar.pack_propagate(False)
        has_folder = bool((self.profile.game_folder_path or "").strip())

        self._apply_canvas = tk.Canvas(
            apply_bar, bg=COLOR_WIDGET, highlightthickness=0,
            cursor="hand2" if has_folder else "",
        )
        self._apply_canvas.pack(fill="both", expand=True)
        self._apply_enabled = [has_folder]
        self._apply_anim_offset = [0]
        _HALF = 30
        self._apply_grad = (
            _color_gradient("#1e3350", "#2e7abf", _HALF) +
            _color_gradient("#2e7abf", "#1e3350", _HALF)
        )
        self._apply_text_id = self._apply_canvas.create_text(
            WINDOW_WIDTH // 2, 22, text=lang.t("buttons.apply"),
            fill=COLOR_TEXT if has_folder else COLOR_TEXT_DIM,
            font=("Segoe UI", 10), anchor="center", tags="apply_text",
        )

        def _center_apply(event=None):
            c = self._apply_canvas
            c.coords(self._apply_text_id, c.winfo_width() / 2, c.winfo_height() / 2)

        self._apply_canvas.bind("<Configure>", _center_apply)
        self._apply_canvas.bind(
            "<Button-1>", lambda _e: self._on_apply() if self._apply_enabled[0] else None
        )
        if has_folder:
            self._start_apply_anim()

        # Scrollable rows
        canvas = tk.Canvas(content, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview,
                                  style="Dark.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        list_frame = tk.Frame(canvas, bg=COLOR_BG)
        win_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")
        list_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        def _on_mousewheel(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        content.bind("<Enter>", lambda _e: content.bind_all("<MouseWheel>", _on_mousewheel))
        content.bind("<Leave>", lambda _e: content.unbind_all("<MouseWheel>"))

        from collections import defaultdict
        groups: dict[str, list] = defaultdict(list)
        for mod in db.mods:
            groups[mod.theme].append(mod)
        for theme, mods in groups.items():
            self._build_theme_category(list_frame, theme, mods)

    def _build_theme_category(self, parent: tk.Frame, theme: str, mods: list) -> None:
        """Collapsable category header grouping mods that share the same theme."""
        expanded = [True]

        cat_header = tk.Frame(parent, bg=COLOR_WIDGET, cursor="hand2")
        cat_header.pack(fill="x")

        indicator = tk.Label(cat_header, text="▼", bg=COLOR_WIDGET, fg=COLOR_TEXT_DIM,
                             font=("Segoe UI", 8), padx=6, pady=5, cursor="hand2")
        indicator.pack(side="left")

        theme_label = tk.Label(cat_header, text=theme, bg=COLOR_WIDGET, fg=COLOR_TEXT,
                               font=("Segoe UI", 9, "bold"), pady=5, cursor="hand2")
        theme_label.pack(side="left")

        rows_frame = tk.Frame(parent, bg=COLOR_BG)
        rows_frame.pack(fill="x")
        for i, mod in enumerate(mods):
            self._build_mod_row(rows_frame, mod, i)

        def toggle(_e=None):
            if expanded[0]:
                rows_frame.pack_forget()
                indicator.configure(text="▶")
            else:
                rows_frame.pack(fill="x", after=cat_header)
                indicator.configure(text="▼")
            expanded[0] = not expanded[0]

        for w in (cat_header, indicator, theme_label):
            w.bind("<Button-1>", toggle)

    def _build_mod_row(self, parent: tk.Frame, mod, index: int) -> None:
        """One row in the mod list: checkbox · name · author · col4 · col5."""
        row_bg = COLOR_BG if index % 2 == 0 else "#232323"
        row = tk.Frame(parent, bg=row_bg, height=14)
        row.pack_propagate(False)
        row.pack(fill="x")
        for i, w in enumerate(_MOD_COL_WIDTHS):
            row.columnconfigure(i, minsize=w)

        is_installed = any(m.name == mod.name for m in self.profile.mods)
        checked = [is_installed]
        disabled = [False]

        cb_label = tk.Label(row, text="☑" if is_installed else "☐", bg=row_bg, fg=COLOR_TEXT,
                            font=("Segoe UI", 9), cursor="hand2")
        cb_label.grid(row=0, column=0, padx=6, pady=0)

        def on_checkbox(_e=None):
            if disabled[0]:
                return
            self.profile.mods = [m for m in self.profile.mods if m.name != mod.name]
            if not checked[0]:
                self.profile.mods.append(InstalledMod(name=mod.name))
                cb_label.configure(text="☑")
                checked[0] = True
            else:
                cb_label.configure(text="☐")
                checked[0] = False
            self._refresh_apply_state()

        cb_label.bind("<Button-1>", on_checkbox)

        name_label = tk.Label(row, text=mod.name, bg=row_bg, fg=COLOR_LINK,
                              font=("Segoe UI", 9, "bold"), anchor="w", cursor="hand2")
        name_label.grid(row=0, column=1, sticky="w", padx=8, pady=0)
        name_label.bind("<Button-1>", lambda _e, url=mod.url_repo: webbrowser.open(url))

        tk.Label(row, text=mod.author, bg=row_bg, fg=COLOR_GOLD,
                 font=("Segoe UI", 9), anchor="w").grid(row=0, column=2, sticky="w", padx=8, pady=0)

        version_btn = tk.Button(row, text="…", bg=row_bg, fg=COLOR_TEXT_DIM,
                                activebackground=COLOR_WIDGET_ACTIVE, activeforeground=COLOR_TEXT,
                                relief="flat", bd=0, font=("Segoe UI", 9),
                                state="disabled", cursor="", padx=6)
        version_btn.grid(row=0, column=3, sticky="w", padx=4, pady=0)

        local_lbl = tk.Label(row, text="…", bg=row_bg, fg=COLOR_TEXT_DIM,
                             font=("Segoe UI", 9), anchor="w")
        local_lbl.grid(row=0, column=4, sticky="w", padx=8, pady=0)

        self._mod_row_refs[mod.name] = {
            "cb_label": cb_label,
            "name_label": name_label,
            "version_btn": version_btn,
            "local_lbl": local_lbl,
            "disabled": disabled,
        }

        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill="x")

    def _on_apply(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(lang.t("apply_dialog.title"))
        dialog.configure(bg=COLOR_BG)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        body = tk.Frame(dialog, bg=COLOR_BG, padx=40, pady=28)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=lang.t("apply_dialog.title"),
                 bg=COLOR_BG, fg=COLOR_TEXT, font=("Segoe UI", 11, "bold")).pack(pady=(0, 12))
        status_lbl = tk.Label(body, text="", bg=COLOR_BG, fg=COLOR_TEXT_DIM,
                              font=("Segoe UI", 10))
        status_lbl.pack()

        self._center_dialog(dialog)
        dialog.update()

        # --- Work ---
        self.log.info(f"Synchronisation started for profile '{self.profile.name}'")

        if not self.profile.path.exists():
            Profile(
                name=self.profile.name,
                app_version=APP_VERSION,
                game_folder_path=self.profile.game_folder_path,
                favorite=self.profile.favorite,
                path=self.profile.path,
            ).save()
            self.log.warning(
                f"Profile file '{self.profile.path.name}' disappeared between launch and apply "
                "— it has been recreated with default content"
            )

        self.profile.save()
        self.log.info(f"Config updated: {len(self.profile.mods)} mod(s) active in '{self.profile.name}'")

        status_lbl.configure(text=lang.t("apply_dialog.config_updated"), fg=COLOR_TEXT)
        dialog.update()

        self._initial_mod_names = {m.name for m in self.profile.mods}
        self.log.info(f"Synchronisation ended for profile '{self.profile.name}'")

        def _finish():
            dialog.destroy()
            self._open_repo_check()

        self.after(1500, _finish)
        self._refresh_apply_state()

    def _start_apply_anim(self) -> None:
        if self._apply_anim_job is not None:
            return
        self._apply_draw_frame()

    def _stop_apply_anim(self) -> None:
        if self._apply_anim_job is not None:
            self.after_cancel(self._apply_anim_job)
            self._apply_anim_job = None
        c = getattr(self, "_apply_canvas", None)
        if c is None:
            return
        c.delete("gradient")
        c.configure(bg=COLOR_WIDGET, cursor="")
        text_id = getattr(self, "_apply_text_id", None)
        if text_id is not None:
            c.itemconfig(text_id, fill=COLOR_TEXT_DIM)

    def _set_apply_waiting(self, waiting: bool) -> None:
        c = getattr(self, "_apply_canvas", None)
        if c is None:
            return
        text_id = getattr(self, "_apply_text_id", None)
        if waiting:
            self._stop_apply_anim()
            self._apply_enabled[0] = False
            if text_id is not None:
                c.itemconfig(text_id, text=lang.t("buttons.waiting"), fill=COLOR_TEXT_DIM)
        else:
            has_folder = bool((self.profile.game_folder_path or "").strip())
            self._apply_enabled[0] = has_folder
            if text_id is not None:
                c.itemconfig(
                    text_id,
                    text=lang.t("buttons.apply"),
                    fill=COLOR_TEXT if has_folder else COLOR_TEXT_DIM,
                )
            if has_folder:
                c.configure(cursor="hand2")
                self._start_apply_anim()
            else:
                c.configure(cursor="")

    def _refresh_apply_state(self) -> None:
        """Re-evaluate the apply button after loading or a checkbox change."""
        c = getattr(self, "_apply_canvas", None)
        if c is None:
            return
        has_folder = bool((self.profile.game_folder_path or "").strip())
        if not has_folder:
            return
        text_id = getattr(self, "_apply_text_id", None)
        no_mods = not self.profile.mods
        needs_update = any(s == "to_update" for s in self._mod_statuses.values())
        has_changes = {m.name for m in self.profile.mods} != self._initial_mod_names
        if no_mods:
            self._stop_apply_anim()
            self._apply_enabled[0] = False
            c.configure(cursor="")
            if text_id is not None:
                c.itemconfig(text_id, text=lang.t("buttons.no_mods"), fill=COLOR_TEXT_DIM)
        elif not needs_update and not has_changes:
            self._stop_apply_anim()
            self._apply_enabled[0] = False
            c.configure(cursor="")
            if text_id is not None:
                c.itemconfig(text_id, text=lang.t("buttons.no_changes"), fill=COLOR_TEXT_DIM)
        else:
            self._apply_enabled[0] = True
            c.configure(cursor="hand2")
            if text_id is not None:
                c.itemconfig(text_id, text=lang.t("buttons.apply"), fill=COLOR_TEXT)
            self._start_apply_anim()

    def _apply_draw_frame(self) -> None:
        c = self._apply_canvas
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            self._apply_anim_job = self.after(40, self._apply_draw_frame)
            return
        c.delete("gradient")
        grad = self._apply_grad
        period = len(grad)
        off = self._apply_anim_offset[0]
        band = 4
        x = 0
        while x < w:
            idx = (x // band + off) % period
            c.create_rectangle(x, 0, x + band, h + 1, fill=grad[idx], outline="", tags="gradient")
            x += band
        c.tag_raise("apply_text")
        self._apply_anim_offset[0] = (off + 1) % period
        self._apply_anim_job = self.after(40, self._apply_draw_frame)

    def _mark_mod_unavailable(self, mod_name: str) -> None:
        """Cross out a mod row and disable its checkbox after a failed repo check."""
        ref = self._mod_row_refs.get(mod_name)
        if ref is None:
            return
        ref["disabled"][0] = True
        ref["cb_label"].configure(text="☐", fg=COLOR_WARN, cursor="")
        ref["name_label"].configure(
            font=tkfont.Font(family="Segoe UI", size=9, weight="bold", overstrike=True),
            fg=COLOR_WARN,
        )

    def _set_mod_releases(self, mod_name: str, versions: list[str], file_version: str | None) -> None:
        """Enable the version dropdown button once releases have been fetched.

        file_version: None = file absent; "" = present but unreadable; "x.y.z" = known version.
        """
        from file_checker import compare_versions, format_version
        ref = self._mod_row_refs.get(mod_name)
        if ref is None:
            return
        btn = ref["version_btn"]
        local_lbl = ref["local_lbl"]

        if not versions:
            btn.configure(text="—", fg=COLOR_TEXT_DIM)
            local_lbl.configure(text="-", fg=COLOR_TEXT_DIM)
            return

        latest = versions[0]

        # Newest version: dropdown listing all releases, user can pick one
        popup_ref = [None]
        selected_version = [latest]

        def _ver_fg(ver: str) -> str:
            if not file_version:
                return COLOR_TEXT
            cmp = compare_versions(ver, file_version)
            if cmp > 0:
                return COLOR_OK
            if cmp < 0:
                return COLOR_WARN
            return COLOR_TEXT

        def on_version_select(version: str) -> None:
            selected_version[0] = version
            btn.configure(text=f"{format_version(version)}  ▾", fg=_ver_fg(version))
            popup_ref[0] = None

        def toggle():
            if popup_ref[0] is not None and popup_ref[0].winfo_exists():
                popup_ref[0].destroy()
                popup_ref[0] = None
            else:
                popup_ref[0] = self._open_version_popup(btn, versions, on_select=on_version_select)

        btn.configure(text=f"{format_version(latest)}  ▾", fg=_ver_fg(latest), state="normal", cursor="hand2", command=toggle)
        self._mod_row_refs[mod_name]["selected_version"] = selected_version

        # Local version: installed file version with status colour
        if file_version is None:
            self._mod_statuses[mod_name] = "latest"
            local_lbl.configure(text="-", fg=COLOR_TEXT_DIM)
        elif file_version == "":
            self._mod_statuses[mod_name] = "up_to_date"
            local_lbl.configure(text="?", fg=COLOR_TEXT_DIM)
        elif compare_versions(file_version, latest) >= 0:
            self._mod_statuses[mod_name] = "up_to_date"
            local_lbl.configure(text=file_version, fg=COLOR_OK)
        else:
            self._mod_statuses[mod_name] = "to_update"
            local_lbl.configure(text=file_version, fg=COLOR_UPDATE)

    def _open_version_popup(self, anchor: tk.Widget, versions: list[str], on_select=None) -> tk.Toplevel:
        """Borderless dropdown listing all release versions below the anchor widget."""
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=COLOR_BORDER)

        anchor.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height()
        popup.geometry(f"+{x}+{y}")

        inner = tk.Frame(popup, bg=COLOR_WIDGET)
        inner.pack(padx=1, pady=1)

        from file_checker import format_version
        for version in versions:
            lbl = tk.Label(inner, text=format_version(version), bg=COLOR_WIDGET, fg=COLOR_TEXT,
                           font=("Segoe UI", 9), anchor="w", padx=12, pady=4, cursor="hand2")
            lbl.pack(fill="x")
            lbl.bind("<Enter>", lambda _e, l=lbl: l.configure(bg=COLOR_WIDGET_ACTIVE))
            lbl.bind("<Leave>", lambda _e, l=lbl: l.configure(bg=COLOR_WIDGET))
            if on_select is not None:
                lbl.bind("<Button-1>", lambda _e, v=version: (on_select(v), popup.destroy()))

        popup.bind("<FocusOut>", lambda _e: popup.destroy())
        popup.bind("<Escape>", lambda _e: popup.destroy())
        popup.focus_set()
        return popup

    def _build_bottom_bar(self) -> None:
        """Bottom bar: language flag (left) and version (right)."""
        bottom_bar = tk.Frame(self, bg=COLOR_BAR, height=28,
                             highlightbackground=COLOR_BORDER, highlightthickness=1)
        bottom_bar.pack(side="bottom", fill="x")
        bottom_bar.pack_propagate(False)
        self.bottom_bar = bottom_bar

        self._lang_popup = None
        self._flag_imgs = {
            name: load_svg_as_photo(svg, height=16)
            for name, svg in _LANG_FLAGS.items()
        }

        self._flag_btn = tk.Label(
            bottom_bar, image=self._flag_imgs[self._current_lang],
            bg=COLOR_BAR, cursor="hand2",
        )
        self._flag_btn.pack(side="left", padx=10)
        self._flag_btn.bind("<Button-1>", lambda _e: self._toggle_lang_popup())

        version = tk.Label(bottom_bar, text=f"v{APP_VERSION}",
                          bg=COLOR_BAR, fg=COLOR_TEXT_DIM, font=("Segoe UI", 9))
        version.pack(side="right", padx=10)

    def _toggle_lang_popup(self) -> None:
        if self._lang_popup is not None:
            self._close_lang_popup()
        else:
            self._open_lang_popup()

    def _close_lang_popup(self) -> None:
        if self._lang_popup is not None:
            self._lang_popup.destroy()
            self._lang_popup = None

    def _open_lang_popup(self) -> None:
        """Horizontal popup to the right of the flag showing all other languages."""
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=COLOR_BORDER)
        self._lang_popup = popup

        self._flag_btn.update_idletasks()
        x = self._flag_btn.winfo_rootx() + self._flag_btn.winfo_width() + 2
        y = self._flag_btn.winfo_rooty()
        popup.geometry(f"+{x}+{y}")

        inner = tk.Frame(popup, bg=COLOR_WIDGET)
        inner.pack(padx=1, pady=1)

        for name, _ in _LANG_FLAGS.items():
            if name == self._current_lang:
                continue
            img = self._flag_imgs[name]
            btn = tk.Label(inner, image=img, bg=COLOR_WIDGET, cursor="hand2", padx=6, pady=4)
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda _e, n=name: self._switch_language(n))
            btn.bind("<Enter>", lambda _e, b=btn: b.configure(bg=COLOR_WIDGET_ACTIVE))
            btn.bind("<Leave>", lambda _e, b=btn: b.configure(bg=COLOR_WIDGET))

        popup.bind("<FocusOut>", lambda _e: self._close_lang_popup())
        popup.bind("<Escape>", lambda _e: self._close_lang_popup())
        popup.focus_set()

    def _switch_language(self, lang_name: str) -> None:
        """Reload strings for lang_name and rebuild the entire UI."""
        self._close_lang_popup()
        if lang_name == self._current_lang:
            return
        self._current_lang = lang_name
        lang.load(lang_name)
        self.log.info(f"Language switched to: {lang_name}")
        if self._blink_job is not None:
            self.after_cancel(self._blink_job)
            self._blink_job = None
        if self._apply_anim_job is not None:
            self.after_cancel(self._apply_anim_job)
            self._apply_anim_job = None
        self._apply_canvas = None
        for widget in self.winfo_children():
            widget.destroy()
        self.title(lang.t("app.title"))
        self._build_top_bar()
        self._build_content()
        self._build_bottom_bar()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._open_repo_check)


def main() -> None:
    app = ModLoaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
