# DockShade 👻


**Terminal UI para herramientas de hacking ético en Kali Linux via Distrobox.**

Navega, aprende y lanza herramientas de pentesting desde una interfaz TUI sin salir de tu entorno de trabajo. DockShade organiza las herramientas por categoría y nivel, explica cuándo y cómo usarlas, y las ejecuta directamente en un contenedor Kali Linux aislado.

![DockShade screenshot](https://raw.githubusercontent.com/iric-Sauldc/dockshade/main/image.png)

---

## ¿Qué hace?

- **32 herramientas** organizadas por categoría (Recon, Web, Exploitation, Passwords, Wireless, Network, Post-Exploitation, Forensics, Reversing)
- **3 niveles de dificultad** — filtra por Básico, Intermedio o Avanzado
- **Búsqueda semántica** — busca por nombre, tag, descripción, caso de uso o troubleshooting
- **Ejemplos navegables** con nivel propio — usa ↑↓ para moverte entre ellos
- **Lanzar en Kali** — abre el comando directamente en el contenedor, la terminal queda como shell interactiva
- **Instalar herramientas** — si una herramienta no está en el contenedor, la instala con un botón
- **Notas personales** por herramienta (guardadas en SQLite local)
- **Favoritos** y **historial** de comandos lanzados
- **Flujos guiados** de pentest — pasos ordenados para cada tipo de engagement
- **Verificación automática** de qué herramientas están realmente instaladas en el contenedor
- **Setup completo** — el instalador configura Docker, Distrobox y el contenedor Kali si no existen

---

## Requisitos

- Linux (Debian, Ubuntu, Kali, Arch, Fedora o derivados)
- Python 3.10+
- Docker (el instalador lo configura si no está)
- Distrobox (el instalador lo configura si no está)

---

## Instalación

```bash
git clone https://github.com/iric-Sauldc/dockshade.git
cd dockshade
chmod +x install.sh
./install.sh
```

El instalador verifica e instala automáticamente:
1. Python 3.10+ y la dependencia `textual`
2. Docker (desde el repositorio oficial)
3. Distrobox
4. El contenedor `kali` con `kalilinux/kali-rolling`

Al terminar, `dockshade` queda disponible como comando global.

```bash
dockshade
```

---

## Desinstalar

```bash
./install.sh --remove
```

Elimina los archivos, el binario y opcionalmente el contenedor Kali.

---

## Uso

| Tecla       | Acción                          |
|-------------|----------------------------------|
| `↑ ↓`       | Navegar ejemplos del panel derecho |
| `Ctrl+L`    | Lanzar comando en Kali          |
| `Ctrl+I`    | Instalar herramienta en Kali    |
| `Ctrl+F`    | Buscar herramienta              |
| `Ctrl+N`    | Editar nota personal            |
| `Ctrl+B`    | Agregar/quitar de favoritos     |
| `Ctrl+H`    | Ver historial global            |
| `Escape`    | Limpiar búsqueda                |
| `q`         | Salir                           |

---

## Estructura del proyecto

```
dockshade/
├── main.py          # Aplicación TUI principal (Textual)
├── db.py            # Capa de persistencia SQLite
├── checker.py       # Verificación de instalación en el contenedor
├── kali_tools.json  # Base de datos de herramientas y flujos
├── install.sh       # Instalador / desinstalador
├── LICENSE          # MIT License
└── README.md
```

---

## Agregar herramientas

Edita `kali_tools.json` siguiendo la estructura existente:

```json
{
  "name": "nombre-herramienta",
  "category": "Web",
  "level": 1,
  "tags": ["tag1", "tag2"],
  "description": "Qué hace la herramienta.",
  "when_to_use": "En qué momento del pentest se usa.",
  "output_guide": "Qué buscar en el output.",
  "chain": ["herramienta-siguiente"],
  "installed": true,
  "examples": [
    {
      "desc": "Descripción del ejemplo",
      "cmd": "comando --flags {target}",
      "level": 1
    }
  ],
  "troubleshooting": [
    "Problema común: solución."
  ]
}
```

Los placeholders disponibles en `cmd` son: `{target}`, `{domain}`, `{canal}`, `{MAC_AP}`, `{hash}`. El modal de lanzamiento pedirá su valor antes de ejecutar.

---

## Herramientas incluidas

| Categoría        | Herramientas |
|-----------------|--------------|
| Recon            | nmap, netdiscover, whois, theHarvester |
| Web              | gobuster, ffuf, nikto, sqlmap, burpsuite, wfuzz, nuclei, feroxbuster |
| Exploitation     | metasploit, searchsploit |
| Passwords        | hydra, john, hashcat |
| Wireless         | aircrack-ng |
| Network          | wireshark, tcpdump, netcat, enum4linux, responder, netexec |
| Post-Exploitation| linpeas, winpeas |
| Forensics        | volatility, binwalk, steghide |
| Reversing        | gdb, strings, strace |

---

## Flujos guiados

DockShade incluye 6 flujos de pentest paso a paso:

- **Reconocimiento Externo** (Básico)
- **Pentest Web Básico** (Básico)
- **Red Interna Windows** (Intermedio)
- **Post-Explotación Linux** (Intermedio)
- **CTF Forense** (Intermedio)
- **Investigación de Vulnerabilidades** (Avanzado)

---

## Stack técnico

- **[Textual](https://textual.textualize.io/)** — framework TUI en Python
- **SQLite** — persistencia de notas, favoritos e historial
- **Distrobox + Docker** — aislamiento del entorno Kali
- **JSON** — base de datos de herramientas extensible


## Aviso legal

DockShade es una herramienta educativa para profesionales de seguridad y estudiantes. Úsala únicamente en sistemas donde tengas autorización explícita. El autor no se hace responsable del uso indebido.

---

## Licencia

MIT — consulta el archivo [LICENSE](LICENSE) para más detalles.
