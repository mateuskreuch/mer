from rich.text import Text
from textual.app import App
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
   Footer,
   Header,
   Input,
   Label,
   ListItem,
   ListView,
   RichLog,
   Static,
)
from textual.message import Message
from textual.screen import ModalScreen

from .color import get_unique_color
from .process import ON_WINDOWS
from .process_manager import ProcessManager

class RunCommandScreen(ModalScreen):
   def __init__(self, process_name: str, cwd: str, **kwargs):
      super().__init__(**kwargs)

      self.process_name = process_name
      self.cwd = cwd

   def compose(self):
      yield Vertical(
         Label(f"Run command in [dim]{self.cwd}[/]:"),
         Input(placeholder="Enter command..."),
         id="run-command-dialog"
      )

   def on_mount(self):
      self.query_one(Input).focus()

   def on_input_submitted(self, event: Input.Submitted):
      command = event.value

      if command:
         import subprocess

         if ON_WINDOWS:
            subprocess.Popen(f'start cmd /k "{command}"', shell=True, cwd=self.cwd)
         else:
            self.app.notify("Running commands is not supported on this OS at this time", severity="warning", timeout=3)

      self.dismiss()

class SetPinnedLogs(Message):
   def __init__(self, name: str, pinned: bool):
      self.name = name
      self.pinned = pinned

      super().__init__()

class ProcessLogs(Widget):
   highlighted_process = reactive[str | None](None)

   def __init__(self, **kwargs):
      super().__init__(**kwargs)

      self._pinned_processes: set[str] = set()

   def compose(self):
      yield Static("", id="log-header")
      yield RichLog(id="log-view", highlight=True, markup=False)

   def watch_highlighted_process(self, value):
      self._rebuild_logs()

   def set_pinned(self, process_name: str, pinned: bool):
      if pinned:
         self._pinned_processes.add(process_name)
      else:
         self._pinned_processes.discard(process_name)

      self._rebuild_logs()

   def get_all_log_sources(self) -> set[str]:
      return self._pinned_processes | ({self.highlighted_process} if self.highlighted_process else set())

   def add_log_line(self, process_name: str, text: str):
      if process_name in self.get_all_log_sources():
         self._write_log(process_name, text)

   def _rebuild_logs(self):
      log_sources = self.get_all_log_sources()

      self.query_one("#log-header", Static).update(", ".join(sorted(log_sources)))

      log_view = self.query_one("#log-view", RichLog)
      log_view.clear()

      if not log_sources:
         return

      all_logs = []

      for name in log_sources:
         for ts, line in ProcessManager().processes[name].logs:
            all_logs.append((ts, name, line))

      all_logs.sort(key=lambda x: x[0])

      for _, name, line in all_logs:
         self._write_log(name, line)

   def _write_log(self, process_name: str, line: str):
      log_view = self.query_one("#log-view", RichLog)
      text = Text()
      color = get_unique_color(process_name)
      text.append(f'{process_name} | ', style=color)
      text.append(line)
      log_view.write(text)

class ProcessItem(ListItem):
   logs_pinned = reactive[bool](False)
   process_running = reactive[bool](False)

   def __init__(self, process_name: str, **kwargs):
      super().__init__(**kwargs)

      self._process_name = process_name

   @property
   def process_name(self):
      return self._process_name

   def compose(self):
      yield Label(self._label())

   def watch_logs_pinned(self, value):
      self._refresh_label()

   def watch_process_running(self, value):
      self._refresh_label()

   def _refresh_label(self):
      try:
         self.query_one(Label).update(self._label())
      except NoMatches:
         pass

   def _label(self):
      text = Text()

      if self.logs_pinned:
         text.append("» ")
      else:
         text.append("  ")

      if self.process_running:
         color = get_unique_color(self._process_name)
         text.append("■ ", style=f"bold {color}")
      else:
         text.append("- ", style="dim")

      text.append(self._process_name)

      return text

class ProcessListView(ListView):
   BINDINGS = [
      Binding("space", "toggle_pinned", "Pin logs"),
      Binding("r", "run_command", "Run command"),
   ]

   async def action_select_cursor(self):
      await ProcessManager().toggle(self.highlighted_child.process_name)

   def action_toggle_pinned(self):
      highlighted = self.highlighted_child

      highlighted.logs_pinned = not highlighted.logs_pinned

      self.post_message(SetPinnedLogs(highlighted.process_name, highlighted.logs_pinned))

   def action_run_command(self):
      highlighted = self.highlighted_child

      process = ProcessManager().processes[highlighted.process_name]

      if process.cwd:
         self.app.push_screen(RunCommandScreen(process.name, process.cwd))
      else:
         self.app.notify("No 'cwd' configured for this process", severity="warning", timeout=3)

class MerApp(App):
   TITLE = "Mer"

   CSS = """
   ProcessLogs {
      height: 1fr;
   }
   #log-view {
      height: 1fr;
   }
   #log-header {
      height: 1;
      background: $primary-darken-2;
      padding: 0 1;
   }
   #sidebar {
      width: 26;
      border-right: solid $primary-darken-2;
   }
   ProcessItem {
      padding: 0 1;
   }
   RunCommandScreen {
      align: center middle;
   }
   #run-command-dialog {
      padding: 1 2;
      background: $panel;
      border: thick $primary;
      width: 70%;
      height: 9;
   }
   #run-command-dialog Label {
      margin-bottom: 1;
   }
   """

   BINDINGS = [
      Binding("q", "quit", "Quit"),
   ]

   def __init__(self):
      super().__init__()

   def compose(self):
      yield Header()

      with Horizontal():
         yield ProcessListView(
            *[ProcessItem(name, id=f"process-item-{name}") for name in ProcessManager().processes],
            id="sidebar",
         )
         with Vertical():
            yield ProcessLogs(id='process-logs')

      yield Footer()

   def on_mount(self):
      def on_log(name, ts, text):
         self.query_one(ProcessLogs).add_log_line(name, text)

      def on_state_change(name, process_running):
         try:
            self.query_one(f"#process-item-{name}", ProcessItem).process_running = process_running
         except NoMatches:
            pass

      ProcessManager().set_callbacks(on_log, on_state_change)

   def on_list_view_highlighted(self, event: ListView.Highlighted):
      if not isinstance(event.item, ProcessItem):
         return

      self.query_one(ProcessLogs).highlighted_process = event.item.process_name

   def on_set_pinned_logs(self, message: SetPinnedLogs):
      self.query_one(ProcessLogs).set_pinned(message.name, message.pinned)