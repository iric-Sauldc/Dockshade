#!/usr/bin/env python3
import json, re, subprocess, sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, Label, Static, Button,
    TextArea, ListView, ListItem, TabPane, TabbedContent,
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, work
from textual.screen import ModalScreen
from textual.worker import get_current_worker
import db, checker

BASE_DIR       = Path(__file__).parent
TOOLS_DB       = BASE_DIR / "dockshade_tools.json"
CONTAINER_NAME = "dockshade"
LEVEL_COLORS   = {1: "green", 2: "yellow", 3: "red"}
LEVEL_LABELS   = {1: "● Básico", 2: "●● Intermedio", 3: "●●● Avanzado"}
PLACEHOLDER_LABELS = {
    "target": "IP / host objetivo",
    "domain": "Dominio",
    "canal":  "Canal WiFi",
    "MAC_AP": "MAC del Access Point",
    "hash":   "Archivo o hash",
}
TERMINALS = [
    ["gnome-terminal", "--"], ["xterm", "-e"], ["konsole", "-e"],
    ["alacritty", "-e"], ["kitty"], ["tilix", "-e"],
    ["xfce4-terminal", "-e"], ["mate-terminal", "-e"],
]
CATEGORIES = [
    "★ Favoritos", "Todas", "Recon", "Web", "Exploitation",
    "Passwords", "Wireless", "Network", "Post-Exploitation",
    "Forensics", "Reversing",
]

def _placeholders(cmd):
    return list(dict.fromkeys(re.findall(r'\{(\w+)\}', cmd)))

def load_data():
    with open(TOOLS_DB, encoding="utf-8") as f:
        raw = json.load(f)
    return raw["tools"], raw.get("pentest_flows", [])

class LaunchModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancelar")]

    def __init__(self, tool, cmd, desc):
        super().__init__()
        self.tool = tool
        self.raw_cmd = cmd
        self.desc = desc
        self.phs = _placeholders(cmd)

    def compose(self):
        with Vertical(id="modal_box"):
            yield Label(f" Lanzar en [{CONTAINER_NAME}]", id="modal_title")
            yield Static(f"\n [bold green]{self.tool['name']}[/bold green]  [dim]{self.desc}[/dim]")
            yield Static(f" [dim]$ {self.raw_cmd}[/dim]\n")
            if self.phs:
                yield Label(" Completa los campos:", classes="modal_section")
                for ph in self.phs:
                    lbl = PLACEHOLDER_LABELS.get(ph, ph)
                    yield Label(f"  {lbl}:", classes="field_label")
                    yield Input(placeholder=f"  {lbl}...", id=f"ph_{ph}", classes="ph_input")
                yield Static("")
            yield Static(" [dim]La terminal queda abierta como shell interactiva.[/dim]\n")
            with Horizontal(id="modal_buttons"):
                yield Button("  Ejecutar ", id="btn_run", variant="success")
                yield Button("  Cancelar ", id="btn_cancel")

    def on_mount(self):
        first = f"ph_{self.phs[0]}" if self.phs else "btn_run"
        try:
            self.query_one(f"#{first}").focus()
        except Exception:
            pass

    def _validate(self):
        ok = True
        for ph in self.phs:
            try:
                inp = self.query_one(f"#ph_{ph}", Input)
                if not inp.value.strip():
                    inp.add_class("input_error")
                    ok = False
                else:
                    inp.remove_class("input_error")
            except Exception:
                pass
        return ok

    def _build(self):
        cmd = self.raw_cmd
        for ph in self.phs:
            try:
                val = self.query_one(f"#ph_{ph}", Input).value.strip() or ph.upper()
            except Exception:
                val = ph.upper()
            cmd = cmd.replace(f"{{{ph}}}", val)
        return cmd

    @on(Input.Changed, ".ph_input")
    def clear_err(self, e):
        e.input.remove_class("input_error")

    @on(Input.Submitted)
    def advance(self, e):
        inputs = list(self.query(".ph_input"))
        try:
            idx = inputs.index(e.input)
            if idx + 1 < len(inputs):
                inputs[idx + 1].focus()
            else:
                self.query_one("#btn_run", Button).focus()
        except ValueError:
            pass

    @on(Button.Pressed, "#btn_run")
    def run(self):
        if self._validate():
            self.dismiss(self._build())

    @on(Button.Pressed, "#btn_cancel")
    def cancel(self):
        self.dismiss(None)


class NoteModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cerrar")]

    def __init__(self, tool_name, note):
        super().__init__()
        self.tool_name = tool_name
        self.note = note

    def compose(self):
        with Vertical(id="modal_box", classes="note_modal"):
            yield Label(f" Notas — {self.tool_name}", id="modal_title")
            yield Static(" [dim]Escribe lo que aprendiste, trucos, comandos propios...[/dim]\n")
            yield TextArea(self.note, id="note_area")
            with Horizontal(id="modal_buttons"):
                yield Button("  Guardar ", id="btn_save", variant="success")
                yield Button("  Cerrar  ", id="btn_close")

    def on_mount(self):
        try:
            self.query_one("#note_area", TextArea).focus()
        except Exception:
            pass

    @on(Button.Pressed, "#btn_save")
    def save(self):
        content = self.query_one("#note_area", TextArea).text
        db.save_note(self.tool_name, content)
        self.dismiss(content)

    @on(Button.Pressed, "#btn_close")
    def close(self):
        self.dismiss(None)


class HistoryModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cerrar")]

    def compose(self):
        history = db.get_history(limit=30)
        with Vertical(id="modal_box", classes="hist_modal"):
            yield Label(" Historial global", id="modal_title")
            with ScrollableContainer():
                if not history:
                    yield Static("\n  [dim]Sin historial aún.[/dim]")
                for e in history:
                    ts = e["ran_at"][:16].replace("T", " ")
                    yield Static(
                        f" [dim]{ts}[/dim]  [cyan]{e['tool_name']}[/cyan]\n"
                        f"  [green]$ {e['command']}[/green]\n"
                    )
            with Horizontal(id="modal_buttons"):
                yield Button("  Cerrar  ", id="btn_close")
                yield Button("  Borrar historial ", id="btn_clear", variant="error")

    @on(Button.Pressed, "#btn_close")
    def close(self):
        self.dismiss(None)

    @on(Button.Pressed, "#btn_clear")
    def clear(self):
        db.clear_history()
        self.dismiss("cleared")


CSS = """
Screen{background:#080810;}
Header{background:#0d0d1f;color:#e94560;height:1;text-style:bold;}
Footer{background:#0d0d1f;color:#4a9eff;height:1;}
#main_layout{layout:horizontal;height:1fr;}
#left_panel{width:22;background:#0a0a18;border-right:solid #1e1e3a;}
#cat_title{color:#e94560;text-style:bold;text-align:center;padding:1 0 0 0;height:2;}
#cat_list{background:#0a0a18;border:none;}
#cat_list > ListItem{background:#0a0a18;color:#555;padding:0 1;height:1;}
#cat_list > ListItem:hover{background:#141428;color:#999;}
#cat_list > ListItem.--highlight{background:#161630;color:#e94560;text-style:bold;}
#center_panel{width:28;background:#0b0b1a;border-right:solid #1e1e3a;}
#search_input{background:#111122;border:solid #1e1e3a;color:#ccc;margin:1 1 0 1;height:3;}
#search_input:focus{border:solid #e94560;}
#level_filter{layout:horizontal;height:1;margin:0 1;}
.lvl_btn{width:1fr;height:1;border:none;background:#111122;color:#444;min-width:1;}
.lvl_btn.active{background:#1a1a3a;color:#e94560;text-style:bold;}
#tools_scroll{height:1fr;}
#tools_list{background:#0b0b1a;border:none;}
#tools_list > ListItem{background:#0b0b1a;color:#888;padding:0 1;height:1;}
#tools_list > ListItem:hover{background:#141428;color:#ddd;}
#tools_list > ListItem.--highlight{background:#141438;color:#4a9eff;text-style:bold;}
#tools_count{color:#333;text-align:center;height:1;}
#right_panel{width:1fr;background:#080810;padding:0;}
TabbedContent{height:1fr;}
TabPane{padding:1 2;}
#detail_name{color:#e94560;text-style:bold;height:2;}
#detail_meta{height:1;margin-bottom:1;}
#detail_when{color:#aaa;margin-bottom:1;}
#detail_status{height:1;margin-bottom:1;}
#detail_chain{color:#555;height:1;margin-bottom:1;}
#examples_title{color:#f0a500;text-style:bold;height:1;margin-top:1;}
#examples_scroll{height:1fr;}
#troubleshoot_title{color:#e94560;text-style:bold;height:1;margin-top:1;}
#action_bar{height:3;background:#0a0a18;border-top:solid #1e1e3a;layout:horizontal;padding:0 1;}
.action_btn{height:3;margin:0 1;min-width:14;}
#btn_install{display:none;}
#checker_status{color:#333;text-align:right;height:3;padding:1 1;width:1fr;}
#flow_left{width:26;border-right:solid #1e1e3a;}
#flow_list{background:#080810;border:none;}
#flow_list > ListItem{background:#080810;color:#888;padding:0 1;height:1;}
#flow_list > ListItem:hover{background:#141428;color:#ddd;}
#flow_list > ListItem.--highlight{background:#141438;color:#4a9eff;text-style:bold;}
#flow_detail{padding:1 2;}
LaunchModal,NoteModal,HistoryModal{align:center middle;}
#modal_box{background:#0f0f22;border:solid #e94560;padding:1 2;width:64;height:auto;max-height:90vh;}
.note_modal{width:70;height:28;}
.hist_modal{width:70;height:32;}
#modal_title{color:#e94560;text-style:bold;border-bottom:solid #1e1e3a;padding-bottom:1;margin-bottom:1;}
.modal_section{color:#f0a500;text-style:bold;margin-top:1;}
.field_label{color:#888;height:1;}
.ph_input{background:#111122;border:solid #2a2a4a;color:#ddd;margin-bottom:1;}
.ph_input.input_error{border:solid #e94560;}
#note_area{height:14;background:#111122;border:solid #2a2a4a;color:#ddd;}
#modal_buttons{margin-top:1;align:center middle;height:3;}
Button{margin:0 1;}
"""


class DockShade(App):
    CSS = CSS
    BINDINGS = [
        Binding("q",      "quit",         "Salir"),
        Binding("ctrl+l", "launch",       "Lanzar"),
        Binding("ctrl+f", "focus_search", "Buscar"),
        Binding("ctrl+n", "edit_note",    "Nota"),
        Binding("ctrl+h", "show_history", "Historial"),
        Binding("ctrl+b", "toggle_fav",   "Favorito"),
        Binding("ctrl+i", "install_tool", "Instalar", show=False),
        Binding("escape", "clear_search", "Limpiar",  show=False),
    ]

    selected_tool    = reactive(None)
    selected_example = reactive(0)
    current_category = reactive("Todas")
    search_query     = reactive("")
    level_filter     = reactive(None)
    favorites        = reactive(frozenset)
    install_statuses = reactive(dict)

    def __init__(self):
        super().__init__()
        self.all_tools, self.flows = load_data()
        db.init_db()

    def compose(self):
        yield Header(show_clock=False)
        with Horizontal(id="main_layout"):
            with Vertical(id="left_panel"):
                yield Label(" DOCKSHADE", id="cat_title")
                with ListView(id="cat_list"):
                    for cat in CATEGORIES:
                        yield ListItem(Label(f"  {cat}"))
            with Vertical(id="center_panel"):
                yield Input(placeholder="  Buscar herramienta, tag, uso...", id="search_input")
                with Horizontal(id="level_filter"):
                    yield Button("Todos",  id="lvl_all", classes="lvl_btn active")
                    yield Button("● Bás",  id="lvl_1",   classes="lvl_btn")
                    yield Button("●● Med", id="lvl_2",   classes="lvl_btn")
                    yield Button("●●● Av", id="lvl_3",   classes="lvl_btn")
                yield Label("", id="tools_count")
                with ScrollableContainer(id="tools_scroll"):
                    yield ListView(id="tools_list")
            with Vertical(id="right_panel"):
                with TabbedContent(id="detail_tabs"):
                    with TabPane("Info", id="tab_info"):
                        yield Label("", id="detail_name")
                        yield Static("", id="detail_meta")
                        yield Static("", id="detail_desc")
                        yield Static("", id="detail_when")
                        yield Static("", id="detail_status")
                        yield Static("", id="detail_chain")
                        yield Label("", id="examples_title")
                        with ScrollableContainer(id="examples_scroll"):
                            yield Static("", id="examples_content")
                        yield Label("", id="troubleshoot_title")
                        yield Static("", id="troubleshoot_content")
                    with TabPane("Notas", id="tab_notes"):
                        yield Static("", id="notes_content")
                        yield Static(
                            "\n  [dim]Sin notas. Presiona [bold]Ctrl+N[/bold] para escribir.[/dim]",
                            id="note_placeholder"
                        )
                    with TabPane("Historial", id="tab_hist"):
                        with ScrollableContainer():
                            yield Static("", id="tool_history")
                    with TabPane("Flujos", id="tab_flows"):
                        with Horizontal():
                            with Vertical(id="flow_left"):
                                with ListView(id="flow_list"):
                                    for flow in self.flows:
                                        lvl = flow.get("level", 1)
                                        c = LEVEL_COLORS.get(lvl, "white")
                                        yield ListItem(Label(
                                            f"  [{c}]{'●' * lvl}[/{c}] {flow['title']}"
                                        ))
                            with ScrollableContainer(id="flow_detail"):
                                yield Static("", id="flow_content")
                with Horizontal(id="action_bar"):
                    yield Label("", id="checker_status")
                    yield Button("★ Fav [^B]",     id="btn_fav",     classes="action_btn")
                    yield Button("✎ Nota [^N]",     id="btn_note",    classes="action_btn")
                    yield Button("⊞ Hist [^H]",     id="btn_hist",    classes="action_btn")
                    yield Button("⬇ Instalar [^I]", id="btn_install", classes="action_btn", variant="warning")
                    yield Button("▶ Lanzar [^L]",   id="btn_launch",  classes="action_btn", variant="success")
        yield Footer()

    def on_mount(self):
        self.title = "DockShade"
        self.sub_title = f"container: {CONTAINER_NAME}"
        self.favorites = frozenset(db.get_favorites())
        defaults = {t["name"]: t.get("installed", True) for t in self.all_tools}
        self.install_statuses = checker.get_cached_statuses(
            [t["name"] for t in self.all_tools], defaults
        )
        cat_list = self.query_one("#cat_list", ListView)
        cat_list.index = CATEGORIES.index("Todas")
        self.current_category = "Todas"
        self._refresh_tools()
        self._start_checker()
        if self.flows:
            self._render_flow(0)

    @work(thread=True)
    def _start_checker(self):
        worker = get_current_worker()
        names = [t["name"] for t in self.all_tools]

        def on_result(name, installed):
            if not worker.is_cancelled:
                self.call_from_thread(self._on_checked, name, installed)

        def on_done():
            if not worker.is_cancelled:
                self.call_from_thread(self._on_done)

        checker.check_all_tools(names, on_result=on_result, on_done=on_done)

    def _on_checked(self, name, installed):
        s = dict(self.install_statuses)
        s[name] = installed
        self.install_statuses = s
        done = sum(1 for v in self.install_statuses.values() if v is not None)
        try:
            self.query_one("#checker_status", Label).update(
                f"[dim]Verificando {done}/{len(self.all_tools)}...[/dim]"
            )
        except Exception:
            pass
        if self.selected_tool and self.selected_tool["name"] == name:
            self._update_status_widget()

    def _on_done(self):
        try:
            self.query_one("#checker_status", Label).update("[dim]✓ Verificación completa[/dim]")
        except Exception:
            pass
        self._refresh_tools()

    def _get_filtered(self):
        cat   = self.current_category
        q     = self.search_query.lower().strip()
        lvl   = self.level_filter
        favs  = self.favorites
        tools = self.all_tools

        if cat == "★ Favoritos":
            tools = [t for t in tools if t["name"] in favs]
        elif cat != "Todas":
            tools = [t for t in tools if t["category"] == cat]

        if lvl is not None:
            tools = [t for t in tools if t.get("level", 1) == lvl]

        if q:
            def match(t):
                hay = " ".join([
                    t["name"], t.get("description", ""), t.get("when_to_use", ""),
                    " ".join(t.get("tags", [])), " ".join(t.get("chain", [])),
                    " ".join(ex.get("desc", "") for ex in t.get("examples", [])),
                    " ".join(t.get("troubleshooting", [])),
                ]).lower()
                return q in hay
            tools = [t for t in tools if match(t)]

        return tools

    def _refresh_tools(self):
        tools_list = self.query_one("#tools_list", ListView)
        filtered   = self._get_filtered()

        try:
            self.query_one("#tools_count", Label).update(
                f"  [dim]{len(filtered)} herramienta(s)[/dim]"
            )
        except Exception:
            pass

        for child in list(tools_list.children):
            child.remove()

        if not filtered:
            tools_list.mount(ListItem(Label("  [dim]Sin resultados[/dim]")))
            self._clear_detail()
            return

        items = []
        for tool in filtered:
            inst      = self.install_statuses.get(tool["name"], tool.get("installed", True))
            fav       = "★ " if tool["name"] in self.favorites else "  "
            no_inst   = "" if inst else " [dim][✗][/dim]"
            l         = tool.get("level", 1)
            c         = LEVEL_COLORS.get(l, "white")
            items.append(ListItem(Label(
                f"{fav}[{c}]{'●' * l}[/{c}] {tool['name']}{no_inst}"
            )))

        tools_list.mount(*items)
        self.call_after_refresh(self._select_first, list(filtered))

    def _select_first(self, snapshot):
        tl       = self.query_one("#tools_list", ListView)
        filtered = self._get_filtered()
        if not filtered or not snapshot:
            return
        try:
            first_name = snapshot[0]["name"]
            try:
                real_idx = next(i for i, t in enumerate(filtered) if t["name"] == first_name)
            except StopIteration:
                real_idx = 0
            if len(tl.children) > real_idx:
                tl.index = real_idx
                self.selected_tool    = filtered[real_idx]
                self.selected_example = 0
                self._update_detail()
        except Exception:
            pass

    def _clear_detail(self):
        self.selected_tool = None
        for wid in [
            "detail_name", "detail_meta", "detail_desc", "detail_when",
            "detail_status", "detail_chain", "examples_title",
            "examples_content", "troubleshoot_title", "troubleshoot_content"
        ]:
            try:
                self.query_one(f"#{wid}").update("")
            except Exception:
                pass

    def _update_detail(self):
        t = self.selected_tool
        if not t:
            return
        l   = t.get("level", 1)
        c   = LEVEL_COLORS.get(l, "white")
        fav = "★" if t["name"] in self.favorites else "☆"
        try:
            self.query_one("#detail_name", Label).update(f"  {fav} {t['name'].upper()}")
            self.query_one("#detail_meta", Static).update(
                f"  [{c}]{LEVEL_LABELS.get(l, '')}[/{c}]  [dim]{t['category']}[/dim]"
            )
            self.query_one("#detail_desc", Static).update(f"  {t.get('description', '')}")
            w = t.get("when_to_use", "")
            if w:
                self.query_one("#detail_when", Static).update(
                    f"  [bold]Cuándo:[/bold] [dim]{w}[/dim]"
                )
            self._update_status_widget()
            chain = t.get("chain", [])
            if chain:
                self.query_one("#detail_chain", Static).update(
                    f"  [dim]Encadena con: {' → '.join(chain)}[/dim]"
                )
        except Exception:
            pass
        self._update_examples()
        self._update_troubleshooting()
        self._update_notes_tab()
        self._update_history_tab()

    def _update_status_widget(self):
        t = self.selected_tool
        if not t:
            return
        inst = self.install_statuses.get(t["name"], t.get("installed", True))
        if inst:
            txt = "  [green]✓ Instalada en el contenedor[/green]"
        else:
            ic  = t.get("install_cmd", f"sudo apt install -y {t['name']}")
            txt = f"  [red]✗ No instalada[/red]  [dim]→ {ic}[/dim]"
        try:
            self.query_one("#detail_status", Static).update(txt)
            btn = self.query_one("#btn_install", Button)
            btn.display = not inst
        except Exception:
            pass

    def _update_examples(self):
        t   = self.selected_tool
        exs = t.get("examples", []) if t else []
        if not exs:
            try:
                self.query_one("#examples_title", Label).update("")
                self.query_one("#examples_content", Static).update("")
            except Exception:
                pass
            return
        idx = min(self.selected_example, len(exs) - 1)
        self.selected_example = idx
        try:
            self.query_one("#examples_title", Label).update(
                f"  EJEMPLOS  ({idx + 1}/{len(exs)})  [dim][↑↓] para navegar[/dim]"
            )
        except Exception:
            pass
        lines = []
        for i, ex in enumerate(exs):
            el = ex.get("level", 1)
            ec = LEVEL_COLORS.get(el, "white")
            if i == idx:
                lines.append(f"  [bold white]▶  {ex['desc']}[/bold white]  [{ec}]{'●' * el}[/{ec}]")
                lines.append(f"  [bold green]  $ {ex['cmd']}[/bold green]")
            else:
                lines.append(f"  [dim]   {ex['desc']}[/dim]")
                lines.append(f"  [dim]   $ {ex['cmd']}[/dim]")
            lines.append("")
        try:
            self.query_one("#examples_content", Static).update("\n".join(lines))
        except Exception:
            pass

    def _update_troubleshooting(self):
        t     = self.selected_tool
        items = t.get("troubleshooting", []) if t else []
        try:
            if not items:
                self.query_one("#troubleshoot_title", Label).update("")
                self.query_one("#troubleshoot_content", Static).update("")
                return
            self.query_one("#troubleshoot_title", Label).update("  TROUBLESHOOTING")
            self.query_one("#troubleshoot_content", Static).update(
                "\n".join(f"  [yellow]▸[/yellow] [dim]{tip}[/dim]" for tip in items)
            )
        except Exception:
            pass

    def _update_notes_tab(self):
        t = self.selected_tool
        if not t:
            return
        note = db.get_note(t["name"])
        try:
            nw = self.query_one("#notes_content", Static)
            ph = self.query_one("#note_placeholder", Static)
            if note.strip():
                nw.update(f"\n  {note.replace(chr(10), chr(10) + '  ')}")
                ph.display = False
            else:
                nw.update("")
                ph.display = True
        except Exception:
            pass

    def _update_history_tab(self):
        t = self.selected_tool
        if not t:
            return
        history = db.get_history(tool_name=t["name"], limit=15)
        try:
            hw = self.query_one("#tool_history", Static)
            if not history:
                hw.update("\n  [dim]Sin historial para esta herramienta.[/dim]")
                return
            lines = []
            for e in history:
                ts = e["ran_at"][:16].replace("T", " ")
                lines.append(f"  [dim]{ts}[/dim]")
                lines.append(f"  [green]$ {e['command']}[/green]\n")
            hw.update("\n".join(lines))
        except Exception:
            pass

    def _render_flow(self, idx):
        if idx < 0 or idx >= len(self.flows):
            return
        flow = self.flows[idx]
        l    = flow.get("level", 1)
        c    = LEVEL_COLORS.get(l, "white")
        lines = [
            f"  [bold]{flow['title']}[/bold]  [{c}]{LEVEL_LABELS.get(l, '')}[/{c}]",
            f"\n  [dim]{flow.get('description', '')}[/dim]\n",
            "  [bold]Pasos:[/bold]\n",
        ]
        for i, step in enumerate(flow.get("steps", []), 1):
            tn   = step["tool"]
            inst = self.install_statuses.get(tn, True)
            im   = "[green]✓[/green]" if inst else "[red]✗[/red]"
            lines.append(f"  {i}. {im} [bold cyan]{tn}[/bold cyan]\n     [dim]{step['action']}[/dim]\n")
        try:
            self.query_one("#flow_content", Static).update("\n".join(lines))
        except Exception:
            pass

    @on(ListView.Selected, "#cat_list")
    def cat_selected(self, event):
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(CATEGORIES):
            self.current_category = CATEGORIES[idx]
            self._refresh_tools()

    @on(ListView.Selected, "#tools_list")
    def tool_selected(self, event):
        filtered = self._get_filtered()
        idx      = event.list_view.index
        if idx is not None and 0 <= idx < len(filtered):
            self.selected_tool    = filtered[idx]
            self.selected_example = 0
            self._update_detail()

    @on(ListView.Selected, "#flow_list")
    def flow_selected(self, event):
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self.flows):
            self._render_flow(idx)

    @on(Input.Changed, "#search_input")
    def search_changed(self, event):
        self.search_query = event.value
        self._refresh_tools()

    @on(Button.Pressed, "#lvl_all")
    def fl_all(self):
        self.level_filter = None
        self._set_lvl_btn("lvl_all")
        self._refresh_tools()

    @on(Button.Pressed, "#lvl_1")
    def fl_1(self):
        self.level_filter = 1
        self._set_lvl_btn("lvl_1")
        self._refresh_tools()

    @on(Button.Pressed, "#lvl_2")
    def fl_2(self):
        self.level_filter = 2
        self._set_lvl_btn("lvl_2")
        self._refresh_tools()

    @on(Button.Pressed, "#lvl_3")
    def fl_3(self):
        self.level_filter = 3
        self._set_lvl_btn("lvl_3")
        self._refresh_tools()

    def _set_lvl_btn(self, active):
        for bid in ["lvl_all", "lvl_1", "lvl_2", "lvl_3"]:
            try:
                btn = self.query_one(f"#{bid}", Button)
                if bid == active:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass

    @on(Button.Pressed, "#btn_launch")
    def bp_launch(self):
        self.action_launch()

    @on(Button.Pressed, "#btn_note")
    def bp_note(self):
        self.action_edit_note()

    @on(Button.Pressed, "#btn_hist")
    def bp_hist(self):
        self.action_show_history()

    @on(Button.Pressed, "#btn_fav")
    def bp_fav(self):
        self.action_toggle_fav()

    @on(Button.Pressed, "#btn_install")
    def bp_install(self):
        self.action_install_tool()

    def action_install_tool(self):
        t = self.selected_tool
        if not t:
            return
        inst = self.install_statuses.get(t["name"], t.get("installed", True))
        if inst:
            self.notify(f"{t['name']} ya está instalada", severity="information")
            return
        name  = t["name"]
        ic    = t.get("install_cmd", f"sudo apt install -y {name}")
        inner = f"echo '─── DockShade: Instalando {name} ───'; echo; {ic}; echo; echo '─── Listo ───'; exec bash"
        dc = ["distrobox", "enter", CONTAINER_NAME, "--", "bash", "-c", inner]
        if self._run_in_terminal(dc):
            self.notify(f"Instalando {t['name']} en [{CONTAINER_NAME}]...", severity="information")
        else:
            self.notify("Sin terminal gráfica disponible", severity="error")

    def action_launch(self):
        t = self.selected_tool
        if not t:
            self.notify("Selecciona una herramienta", severity="warning")
            return
        exs = t.get("examples", [])
        if not exs:
            self.notify("Sin ejemplos de comando", severity="warning")
            return
        ex = exs[min(self.selected_example, len(exs) - 1)]

        def handle(result):
            if result:
                self._launch(t["name"], result)

        self.push_screen(LaunchModal(t, ex["cmd"], ex.get("desc", "")), handle)

    def action_edit_note(self):
        t = self.selected_tool
        if not t:
            self.notify("Selecciona una herramienta", severity="warning")
            return

        def handle(result):
            if result is not None:
                self.notify(f"✓ Nota guardada — {t['name']}", severity="information")
                self._update_notes_tab()

        self.push_screen(NoteModal(t["name"], db.get_note(t["name"])), handle)

    def action_show_history(self):
        def handle(result):
            if result == "cleared":
                self.notify("Historial borrado", severity="information")
                if self.selected_tool:
                    self._update_history_tab()

        self.push_screen(HistoryModal(), handle)

    def action_toggle_fav(self):
        t = self.selected_tool
        if not t:
            return
        db.toggle_favorite(t["name"])
        self.favorites = frozenset(db.get_favorites())
        is_fav = t["name"] in self.favorites
        self.notify(
            f"★ {t['name']} en favoritos" if is_fav else f"☆ {t['name']} quitado de favoritos",
            severity="information"
        )
        self._update_detail()
        self._refresh_tools()

    def on_key(self, event):
        focused = self.focused
        if focused and focused.__class__.__name__ in ("ListView", "Input", "TextArea"):
            return
        if event.key == "up":
            event.stop()
            t = self.selected_tool
            if t:
                exs = t.get("examples", [])
                if exs:
                    self.selected_example = (self.selected_example - 1) % len(exs)
                    self._update_examples()
        elif event.key == "down":
            event.stop()
            t = self.selected_tool
            if t:
                exs = t.get("examples", [])
                if exs:
                    self.selected_example = (self.selected_example + 1) % len(exs)
                    self._update_examples()

    def action_focus_search(self):
        try:
            self.query_one("#search_input", Input).focus()
        except Exception:
            pass

    def action_clear_search(self):
        try:
            inp = self.query_one("#search_input", Input)
            inp.value = ""
            self.search_query = ""
            self._refresh_tools()
        except Exception:
            pass

    def _run_in_terminal(self, cmd_list):
        for tp in TERMINALS:
            try:
                subprocess.Popen(
                    tp + cmd_list,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except FileNotFoundError:
                continue
        return False

    def _copy_to_clipboard(self, text):
        for cc in [["xclip", "-selection", "clipboard"], ["wl-copy"]]:
            try:
                subprocess.run(cc, input=text.encode(), check=True, capture_output=True)
                return True
            except Exception:
                continue
        return False

    def _launch(self, tool_name, cmd):
        inner = f"echo '─── DockShade: {tool_name} ───'; echo; {cmd}; echo; exec bash"
        dc    = ["distrobox", "enter", CONTAINER_NAME, "--", "bash", "-c", inner]
        if self._run_in_terminal(dc):
            db.add_history(tool_name, cmd)
            db.record_tool_use(tool_name)
            self._update_history_tab()
            self.notify(f"✓ {tool_name} lanzado en [{CONTAINER_NAME}]", severity="information")
        else:
            flat = " ".join(dc)
            if self._copy_to_clipboard(flat):
                self.notify("Sin terminal gráfica — comando copiado al clipboard", severity="warning")
            else:
                self.notify(f"Ejecuta: {flat}", severity="error")


if __name__ == "__main__":
    if not TOOLS_DB.exists():
        print(f"Error: no se encontró {TOOLS_DB}")
        sys.exit(1)
    DockShade().run()
