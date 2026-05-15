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

   @property
   def name(self):
      return self._name

   @property
   def needs(self):
      return self._needs

   @property
   def is_running(self):
      return self._running

   @property
   def logs(self) -> list[tuple[float, str]]:
      return self._logs

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
         self._running = True
         asyncio.ensure_future(self._stream_output())

      except:
         pass

   if ON_WINDOWS:
      def terminate(self):
         try:
            subprocess.call(
               ['taskkill', '/F', '/T', '/PID', str(self._process.pid)],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._running = False

         except:
            pass
   else:
      def terminate(self, sig = signal.SIGTERM):
         try:
            os.killpg(self._process.pid, sig)
            self._running = False

         except:
            pass

   if ON_WINDOWS:
      def kill(self):
         self.terminate()
   else:
      def kill(self):
         self.terminate(signal.SIGKILL)

   async def _stream_output(self) -> None:
      try:
         while True:
            line = await self._process.stdout.readline()
            if not line:
               break
            self._logs.append((time.time_ns(), line.decode(errors="replace").rstrip("\r\n")))
      finally:
         self._running = False