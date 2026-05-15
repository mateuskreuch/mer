from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
   Footer,
   Header,
   Label,
   ListItem,
   ListView,
   RichLog,
   Static,
)

from color import get_unique_color
from process import Process
from process_manager import ProcessManager, load_yml

class ProcessLogs(Widget):
   selected_process = reactive[str | None](None)

   def __init__(self, **kwargs) -> None:
      super().__init__(**kwargs)
      self._pinned_processes: set[str] = set()
      self._logged_lines: dict[str, int] = {}

   def compose(self) -> ComposeResult:
      yield Static("", id="log-header")
      yield RichLog(id="log-view", highlight=True, markup=False)

   def on_mount(self) -> None:
      self.set_interval(0.2, self._update_logs)

   def watch_selected_process(self, value: str | None) -> None:
      self._rebuild_logs()

   def toggle_pinned(self, process_name: str, is_selected: bool) -> None:
      if is_selected:
         self._pinned_processes.add(process_name)
      else:
         self._pinned_processes.discard(process_name)

      self._rebuild_logs()

   def get_all_log_sources(self) -> set[str]:
      return self._pinned_processes | ({self.selected_process} if self.selected_process else set())

   def _rebuild_logs(self) -> None:
      log_view = self.query_one("#log-view", RichLog)

      log_view.clear()
      log_sources = self.get_all_log_sources()

      self._logged_lines = {name: 0 for name in log_sources}

      header_text = ", ".join(sorted(log_sources))

      self.query_one("#log-header", Static).update(header_text)

      self._update_logs()

   def _update_logs(self) -> None:
      log_sources = self.get_all_log_sources()

      if not log_sources:
         return

      all_new_logs: list[tuple[float, str, str]] = []

      # We can't use type hints for app here easily without circular imports or TYPE_CHECKING
      # but we know it's MerApp.
      process_manager = self.app.process_manager

      for name in log_sources:
         process = process_manager.processes[name]
         last_index = self._logged_lines.get(name, 0)
         new_entries = process.logs[last_index:]

         for ts, line in new_entries:
            all_new_logs.append((ts, name, line))

         self._logged_lines[name] = len(process.logs)

      if not all_new_logs:
         return

      all_new_logs.sort(key=lambda x: x[0])

      log_view = self.query_one("#log-view", RichLog)

      for _, name, line in all_new_logs:
         text = Text()
         color = get_unique_color(name)
         text.append(f'{name} | ', style=color)
         text.append(line)
         log_view.write(text)

class ProcessItem(ListItem):
   def __init__(self, process: Process) -> None:
      super().__init__()
      self._process = process
      self._pinned = False

   def compose(self) -> ComposeResult:
      yield Label(self._label())

   def refresh_label(self) -> None:
      self.query_one(Label).update(self._label())

   @property
   def pinned(self) -> bool:
      return self._pinned

   @pinned.setter
   def pinned(self, value: bool) -> None:
      self._pinned = value

   @property
   def process(self):
      return self._process

   def _label(self) -> Text:
      text = Text()

      if self._pinned:
         text.append("✓ ", style="bold green")
      else:
         text.append("  ")

      if self._process.is_running:
         color = get_unique_color(self._process.name)
         text.append("● ", style=f"bold {color}")
      else:
         text.append("○ ", style="dim")

      text.append(self._process.name)

      return text

class ProcessListView(ListView):
   BINDINGS = [
      Binding("space", "toggle_pinned", "Pin logs"),
   ]

   async def action_select_cursor(self) -> None:
      highlighted = self.highlighted_child

      if isinstance(highlighted, ProcessItem):
         app: MerApp = self.app

         await app.process_manager.toggle(highlighted.process.name)

         for item in self.query(ProcessItem):
            item.refresh_label()

   def action_toggle_pinned(self) -> None:
      highlighted = self.highlighted_child

      if isinstance(highlighted, ProcessItem):
         highlighted.pinned = not highlighted.pinned
         highlighted.refresh_label()
         app: MerApp = self.app
         app.toggle_pinned(highlighted.process.name, highlighted.pinned)

class MerApp(App):
   TITLE = "MerApp"

   CSS = """
   ProcessLogs {
      height: 1fr;
   }
   #log-view {
      height: 1fr;
   }
   #sidebar {
      width: 26;
      border-right: solid $primary-darken-2;
   }
   #log-header {
      height: 1;
      background: $primary-darken-2;
      padding: 0 1;
   }
   TabbedContent {
      height: 1fr;
   }
   ProcessItem {
      padding: 0 1;
   }
   #stats-input-row {
      height: auto;
      border-top: solid $primary-darken-2;
   }
   #stats-prompt {
      height: 1;
      padding: 0 1;
      color: $success;
   }
   #stats-input {
      border: none;
   }
   """

   BINDINGS = [
      Binding("q", "quit", "Quit"),
   ]

   def __init__(self) -> None:
      super().__init__()

      self._process_manager = ProcessManager(load_yml())

   @property
   def process_manager(self):
      return self._process_manager

   def compose(self) -> ComposeResult:
      yield Header()

      with Horizontal():
         yield ProcessListView(
            *[ProcessItem(p) for p in self._process_manager.processes.values()],
            id="sidebar",
         )

         with Vertical():
            yield ProcessLogs()

      yield Footer()

   def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
      if not isinstance(event.item, ProcessItem):
         return

      self.query_one(ProcessLogs).selected_process = event.item.process.name

   def toggle_pinned(self, process_name: str, is_selected: bool) -> None:
      self.query_one(ProcessLogs).toggle_pinned(process_name, is_selected)