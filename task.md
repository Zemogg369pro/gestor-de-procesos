# Ruta de Aprendizaje e Implementación del Simulador

Este archivo es tu guía de tareas interactiva. Puedes ir marcando las casillas con una `[x]` a medida que completes cada objetivo de estudio y experimentación práctica.

---

## 📋 FASE 1: Análisis y Comprensión del Código (Lectura)
*Objetivo: Dominar el flujo de datos y el ciclo de vida del simulador.*

- [ ] **1.1 Comprender la Representación del Proceso ([src/core/process.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/core/process.py))**
  - [ ] Estudiar los estados en `ProcessState` y las razones de finalización en `ExitReason`.
  - [ ] Analizar el diccionario `VALID_TRANSITIONS` (FSM) que controla las transiciones de estado válidas.
  - [ ] Analizar el método `PCB.transition()` y ver cómo valida las transiciones de estado legales.
  - [ ] Observar cómo funciona la inicialización y autogeneración de PIDs/atributos en `__post_init__()`.

- [ ] **1.2 Comprender los Límites de Hardware ([src/core/resource.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/core/resource.py))**
  - [ ] Entender las variables de capacidad de `ResourcePool` (`available_cpu` y `available_ram`).
  - [ ] Analizar cómo `request()` resta los recursos solicitados y qué validaciones ejecuta.
  - [ ] Analizar cómo `release()` devuelve recursos al sistema evitando la liberación excesiva ("double-free").

- [ ] **1.3 Dominar el Motor del Planificador ([src/core/scheduler.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/core/scheduler.py))**
  - [ ] Estudiar las colas principales del sistema (`ready_queue` y `waiting_queue`).
  - [ ] Rastrear el flujo del método central `execute_cycle()`, comprendiendo en qué orden se procesan las llegadas, bloqueos por I/O, despacho y ticks de ejecución.
  - [ ] Comparar las políticas de despacho en `_select_next()` para `FCFS` y `SJF`.
  - [ ] Estudiar cómo `_execute_tick()` simula solicitudes aleatorias de I/O basándose en `IO_PROBABILITY`.

- [ ] **1.4 Estudiar la Concurrencia e IPC ([src/ipc/producer_consumer.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/ipc/producer_consumer.py))**
  - [ ] Analizar la creación de hilos independientes (`threading.Thread`) para productores y consumidores.
  - [ ] Entender la sección crítica protegida por `mutex` (`threading.Lock`).
  - [ ] Comprender cómo los semáforos `empty` y `full` actúan como contadores coordinados para regular el flujo del buffer.

---

## 🛠️ FASE 2: Experimentación y Modificaciones Prácticas (Nivel Básico)
*Objetivo: Modificar variables y observar el impacto en el comportamiento del simulador.*

- [ ] **2.1 Alterar la Frecuencia de Bloqueo por Entrada/Salida (I/O)**
  - [ ] En [src/core/scheduler.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/core/scheduler.py#L24-L26), cambiar `IO_PROBABILITY` de `0.10` a `0.30` (30%).
  - [ ] Modificar los límites de tiempo de espera (`IO_WAIT_MIN` y `IO_WAIT_MAX`) a valores más altos.
  - [ ] Ejecutar el simulador y analizar cómo aumenta el tamaño de la cola `WAITING`.

- [ ] **2.2 Personalizar la Capacidad Inicial de Hardware**
  - [ ] En [main.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/main.py), buscar dónde se instancia `ResourcePool` y cambiar la RAM por defecto a `2048 MB` o la CPU a `2 núcleos`.
  - [ ] Observar cómo los procesos con requerimientos altos son rechazados temporalmente de la cola `READY` debido a la falta de RAM libre.

- [ ] **2.3 Variar el Tamaño del Buffer IPC**
  - [ ] En [src/ipc/producer_consumer.py](file:///c:/Users/adria/Downloads/Dante/simulador-gestor-procesos-main/simulador-gestor-procesos-main/src/ipc/producer_consumer.py#L13-L14), modificar `BUFFER_SIZE` a `10` y los `ITEMS_PER_PRODUCER` a `8`.
  - [ ] Ejecutar la demo IPC desde la GUI y validar si se ejecutan más operaciones concurrentes y si el buffer alcanza mayor ocupación.

---

## 🚀 FASE 3: Ampliación del Sistema (Nivel Avanzado)
*Objetivo: Agregar características y algoritmos nuevos al código.*

- [ ] **3.1 Implementar el Algoritmo Round Robin (RR)**
  - [ ] Añadir `ROUND_ROBIN` a la enumeración `SchedulingAlgorithm` en `src/core/scheduler.py`.
  - [ ] Definir un "quantum" (por ejemplo, `quantum = 3 ticks`).
  - [ ] En `execute_cycle()`, controlar el tiempo que el proceso actual lleva corriendo en CPU de forma consecutiva. Si alcanza el quantum y quedan ticks pendientes, desalojarlo, hacer `transition(ProcessState.READY)`, moverlo al final de la `ready_queue` y liberar la CPU.
  - [ ] Actualizar la interfaz en `main.py` para incluir la opción "Round Robin" en el ComboBox de selección.

- [ ] **3.2 Agregar un Estado de Suspensión (Swapping)**
  - [ ] Añadir `SUSPENDED` a `ProcessState` en `src/core/process.py` y configurar transiciones en `VALID_TRANSITIONS`.
  - [ ] Implementar un mecanismo de swap en el planificador: si un nuevo proceso llega y no hay memoria RAM libre, suspender temporalmente un proceso que esté en estado `WAITING` (liberando su RAM) y enviarlo a `SUSPENDED`.
  - [ ] Al liberar RAM, volver a despertar al proceso suspendido.

---

## 🧪 FASE 4: Pruebas y Validación
*Objetivo: Asegurar que el simulador funciona correctamente bajo condiciones límite.*

- [ ] **4.1 Ejecutar Prueba de Estrés (Batch Grande)**
  - [ ] Configurar la simulación con `50` o `100` procesos en modo batch.
  - [ ] Verificar que no existan inconsistencias de memoria (la RAM libre debe retornar exactamente a su valor total al finalizar la simulación).
  - [ ] Verificar que no existan procesos atascados indefinidamente en colas en el modo SJF (problema de inanición o starvation).
