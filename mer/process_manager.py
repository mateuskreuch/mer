import asyncio
import yaml
from .process import Process

YML_PATH = 'processes.yml'

def load_yml(path: str) -> dict[str, Process]:
   with open(path, "r", encoding="utf-8") as f:
      data = yaml.safe_load(f)

   return {
      name : Process(
         name=name,
         run=config["run"],
         cwd=config.get("cwd"),
         needs=set(config.get("needs", [])),
         stop_if_unneeded=config.get("stop-if-unneeded", False),
         ready_when_log=config.get("ready-when-log")
      )
      for name, config in data.items()
   }

class SingletonMeta(type):
   _instances = {}

   def __call__(cls, *args, **kwargs):
      if cls not in cls._instances:
         cls._instances[cls] = super().__call__(*args, **kwargs)

      return cls._instances[cls]

class ProcessManager(metaclass=SingletonMeta):
   def __init__(self, processes: dict[str, Process] = None):
      self._processes = processes or load_yml(YML_PATH)
      self._dependency_order: dict[str, list[str]] = {}
      self._on_log = None
      self._on_state_change = None

   def set_callbacks(self, on_log, on_state_change):
      self._on_log = on_log
      self._on_state_change = on_state_change

      for process in self._processes.values():
         process.set_callbacks(self._on_log, self._on_state_change)

   @property
   def processes(self):
      return self._processes

   def toggle(self, name: str):
      if self._processes[name].is_running:
         self.stop(name)
      else:
         self.start(name)

   def start(self, name: str):
      asyncio.create_task(self._start(name))

   def stop(self, name: str):
      if not self._processes[name].is_running:
         return

      self._processes[name].terminate()

      for other_name in self._processes[name].needs:
         other = self._processes[other_name]

         if other.stop_if_unneeded and other.is_running and not self.is_needed(other_name):
            self.stop(other_name)

   def is_needed(self, name: str) -> bool:
      for other in self._processes.values():
         if other.is_running and name in other.needs:
            return True

      return False

   async def _start(self, name: str):
      if self._processes[name].is_running:
         return

      if name not in self._dependency_order:
         self._dependency_order[name] = self._get_dependency_order(name)

      for n in self._dependency_order[name]:
         process = self._processes[n]

         if not process.is_running:
            await process.start()

   def _get_dependency_order(self, name: str) -> list[str]:
      order = []
      visiting = set()
      visited = set()

      def dfs(n):
         if n in visiting:
            raise ValueError(f"Cycle detected involving '{n}'")

         if n in visited:
            return

         visiting.add(n)

         for dep in self._processes[n].needs:
            if dep not in self._processes:
               raise KeyError(f"Process '{n}' needs unknown process '{dep}'")

            dfs(dep)

         visiting.discard(n)
         visited.add(n)
         order.append(n)

      dfs(name)

      return order