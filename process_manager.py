import yaml
from process import Process

YML_PATH = 'processes.yml'

def load_yml() -> dict[str, Process]:
   with open(YML_PATH, "r", encoding="utf-8") as f:
      data = yaml.safe_load(f)

   return {
      name : Process(
         name=name,
         run=config["run"],
         cwd=config.get("cwd"),
         needs=config.get("needs", []),
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
      self._processes = processes or load_yml()
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

   async def toggle(self, name):
      if self._processes[name].is_running:
         self.stop(name)
      else:
         await self.start(name)

   async def start(self, name):
      if name not in self._dependency_order:
         self._dependency_order[name] = self._get_dependency_order(name)

      for n in self._dependency_order[name]:
         process = self._processes[n]

         if not process.is_running:
            await process.start()

   def stop(self, name):
      self._processes[name].terminate()

   def _get_dependency_order(self, name: str) -> list[str]:
      order = []
      visiting = set()
      visited = set()

      def dfs(n):
         if n not in self._processes:
            raise KeyError(f"Unknown process '{n}'")

         if n in visiting:
            raise ValueError(f"Cycle detected involving '{n}'")

         if n in visited:
            return

         visiting.add(n)

         for dep in self._processes[n].needs:
            dfs(dep)

         visiting.discard(n)
         visited.add(n)
         order.append(n)

      dfs(name)

      return order