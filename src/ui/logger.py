"""
Módulo: logger.py — Sistema de Logging del SO Simulado

Almacena y formatea eventos del kernel simulado.
"""

import time
from dataclasses import dataclass

@dataclass
class LogEntry:
    """Una entrada individual del log."""
    tick: int
    timestamp: float
    message: str

    def __str__(self) -> str:
        # Formato de salida: [Tick XXX | HH:MM:SS] Mensaje
        t = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[Tick {self.tick:>4} | {t}] {self.message}"

class Logger:
    """Sistema de logging que almacena e imprime eventos."""

    def __init__(self, verbose: bool = True) -> None:
        # Almacenamiento en memoria de todos los registros del kernel
        self.entries: list[LogEntry] = []
        self.verbose: bool = verbose

    def log(self, message: str, tick: int = 0) -> None:
        """Registra y opcionalmente imprime un evento."""
        entry = LogEntry(
            tick=tick,
            timestamp=time.time(),
            message=message,
        )
        self.entries.append(entry)

        # Imprimir en consola en tiempo real si verbose está activo
        if self.verbose:
            print(f"  {entry}")

    def show_history(self, last_n: int = 0) -> None:
        """Muestra el historial guardado en consola."""
        print("\n" + "=" * 65)
        print("              HISTORIAL DEL LOG DEL SISTEMA")
        print("=" * 65)

        # Filtrar últimas N entradas si se solicita
        entries = self.entries[-last_n:] if last_n > 0 else self.entries

        if not entries:
            print("  (sin entradas)")
        else:
            for entry in entries:
                print(f"  {entry}")

        print("=" * 65)

    def clear(self) -> None:
        """Borra todos los registros."""
        self.entries.clear()
