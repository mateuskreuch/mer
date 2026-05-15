import asyncio
import os
import signal
import sys
import time

ON_WINDOWS = 'win32' in str(sys.platform).lower()
CREATE_NO_WINDOW = 0x08000000

if ON_WINDOWS:
   import subprocess

def _compat_kwargs() -> dict:
   kwargs = {}

   if ON_WINDOWS:
      kwargs["creationflags"] = CREATE_NO_WINDOW
   else:
      kwargs["start_new_session"] = True

   return kwargs

class Process:
   def __init__(self, name: str, run: str, cwd: str, needs: list[str]):
      self._name = name
      self._run = run
      self._cwd = cwd
      self._needs = needs
      self._running = False
      self._logs: list[tuple[float, str]] = []
      self._on_log = None
      self._on_state_change = None

   @property
   def name(self):
      return self._name

   @property
   def needs(self):
      return self._needs

   @property
   def is_running(self):
      return self._running

   @is_running.setter
   def is_running(self, value):
      self._running = value

      if self._on_state_change:
         self._on_state_change(self._name, value)

   @property
   def logs(self):
      return self._logs

   def set_callbacks(self, on_log, on_state_change):
      self._on_log = on_log
      self._on_state_change = on_state_change

   async def start(self):
      try:
         self._process = await asyncio.create_subprocess_shell(
               self._run,
               cwd=self._cwd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.STDOUT,
               shell=True,
               close_fds=not ON_WINDOWS,
               **_compat_kwargs()
         )
         self.is_running = True

         asyncio.ensure_future(self._stream_output())

      except:
         pass

   if ON_WINDOWS:
      def terminate(self):
         try:
            subprocess.call(
               ['taskkill', '/F', '/T', '/PID', str(self._process.pid)],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self.is_running = False

         except:
            pass
   else:
      def terminate(self, sig = signal.SIGTERM):
         try:
            os.killpg(self._process.pid, sig)

            self.is_running = False

         except:
            pass

   if ON_WINDOWS:
      def kill(self):
         self.terminate()
   else:
      def kill(self):
         self.terminate(signal.SIGKILL)

   async def _stream_output(self):
      try:
         while True:
            line = await self._process.stdout.readline()

            if not line:
               break

            ts = time.time_ns()
            text = line.decode(errors="replace").rstrip("\r\n")

            self._add_log(ts, text)

      finally:
         self.is_running = False

   def _add_log(self, timestamp, text):
      self._logs.append((timestamp, text))

      if self._on_log:
         self._on_log(self._name, timestamp, text)