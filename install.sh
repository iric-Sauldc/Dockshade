#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓${NC}  $*"; }
warn() { echo -e "${YELLOW}  !${NC}  $*"; }
err()  { echo -e "${RED}  ✗${NC}  $*"; }
hdr()  { echo -e "\n${BOLD}${CYAN}$*${NC}"; }
ask()  { echo -e "${YELLOW}  ?${NC}  $*"; }

APP_NAME="dockshade"
#DISTRO="kali"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
BIN_PATH="$BIN_DIR/$APP_NAME"
CONTAINER_NAME="$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_container_exists() {
    local db_cmd
    db_cmd=$(command -v distrobox 2>/dev/null || echo "$HOME/.local/bin/distrobox")
    [[ -x "$db_cmd" ]] || return 1
    "$db_cmd" list --no-color 2>/dev/null \
        | awk -F'|' '{gsub(/ /,"",$2); print $2}' \
        | grep -qx "$CONTAINER_NAME"
}

_remove() {
    hdr "Desinstalando $APP_NAME..."
    [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR" && ok "Archivos eliminados: $INSTALL_DIR"
    [[ -f "$BIN_PATH"    ]] && rm -f  "$BIN_PATH"    && ok "Binario eliminado:   $BIN_PATH"
    echo ""
    ask "¿Eliminar también el contenedor '$CONTAINER_NAME' de Distrobox? [s/N]"
    read -r resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
        if command -v distrobox &>/dev/null || [[ -x "$HOME/.local/bin/distrobox" ]]; then
            local db_cmd
            db_cmd=$(command -v distrobox 2>/dev/null || echo "$HOME/.local/bin/distrobox")
            if _container_exists; then
                "$db_cmd" rm "$CONTAINER_NAME" --force 2>/dev/null \
                    && ok "Contenedor '$CONTAINER_NAME' eliminado" \
                    || warn "No se pudo eliminar el contenedor"
            else
                warn "El contenedor '$CONTAINER_NAME' no existe"
            fi
        else
            warn "Distrobox no disponible"
        fi
    fi
    echo -e "\n${GREEN}$APP_NAME desinstalado.${NC}"
    exit 0
}

if [[ "${1:-}" == "--remove" ]]; then
    _remove
fi

echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  DockShade — Setup               ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════╝${NC}\n"

hdr "1/6  Verificando Python..."
if ! command -v python3 &>/dev/null; then
    err "Python3 no encontrado. Instala con: sudo apt install python3"
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJ" -lt 3 || ( "$PY_MAJ" -eq 3 && "$PY_MIN" -lt 10 ) ]]; then
    err "Se requiere Python 3.10+. Encontrado: $PY_VER"
    exit 1
fi
ok "Python $PY_VER"

hdr "2/6  Verificando textual..."
if ! python3 -c "import textual" &>/dev/null; then
    warn "textual no instalado. Instalando..."
    pip install textual --break-system-packages -q \
        && ok "textual instalado" \
        || { err "Fallo al instalar textual. Ejecuta: pip install textual"; exit 1; }
else
    TV=$(python3 -c "import textual; print(textual.__version__)")
    ok "textual $TV"
fi

hdr "3/6  Verificando Docker..."
if ! command -v docker &>/dev/null; then
    warn "Docker no encontrado"
    ask "¿Instalar Docker? [S/n]"
    read -r resp
    if [[ ! "$resp" =~ ^[nN]$ ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y ca-certificates curl gnupg lsb-release
            sudo install -m 0755 -d /etc/apt/keyrings
            curl -fsSL "https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg" \
                | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            sudo chmod a+r /etc/apt/keyrings/docker.gpg
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
$(lsb_release -cs) stable" \
                | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update -qq
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
                docker-buildx-plugin docker-compose-plugin
            sudo systemctl enable docker --now
            sudo usermod -aG docker "$USER"
            ok "Docker instalado — cierra sesión y vuelve a entrar para aplicar el grupo docker"
        else
            err "Instalación automática solo disponible en sistemas apt"
            echo "     Instala Docker: https://docs.docker.com/engine/install/"
            exit 1
        fi
    else
        warn "Docker omitido. Distrobox lo necesita."
    fi
else
    DV=$(docker --version 2>/dev/null | grep -oP '[\d.]+' | head -1)
    if ! docker info &>/dev/null 2>&1; then
        warn "Docker instalado pero el daemon no está corriendo"
        ask "¿Iniciar Docker? [S/n]"
        read -r resp
        if [[ ! "$resp" =~ ^[nN]$ ]]; then
            sudo systemctl start docker \
                && ok "Docker daemon iniciado" \
                || warn "No se pudo iniciar Docker automáticamente"
        fi
    else
        ok "Docker $DV"
    fi
fi

hdr "4/6  Verificando Distrobox..."
if ! command -v distrobox &>/dev/null && [[ ! -x "$HOME/.local/bin/distrobox" ]]; then
    warn "Distrobox no encontrado"
    ask "¿Instalar Distrobox? [S/n]"
    read -r resp
    if [[ ! "$resp" =~ ^[nN]$ ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y distrobox 2>/dev/null || {
                warn "No disponible en apt, instalando desde script oficial..."
                curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install \
                    | sh -s -- --prefix "$HOME/.local"
            }
        else
            curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install \
                | sh -s -- --prefix "$HOME/.local"
        fi
        if command -v distrobox &>/dev/null || [[ -x "$HOME/.local/bin/distrobox" ]]; then
            ok "Distrobox instalado"
        else
            err "No se pudo instalar Distrobox. Instala manualmente: https://distrobox.it"
            exit 1
        fi
    else
        warn "Distrobox omitido. DockShade no podrá lanzar herramientas."
    fi
else
    DBV=$(distrobox --version 2>/dev/null | grep -oP '[\d.]+' | head -1 || echo "?")
    ok "Distrobox $DBV"
fi

hdr "5/6  Verificando contenedor '$CONTAINER_NAME'..."
DB_CMD=$(command -v distrobox 2>/dev/null || echo "$HOME/.local/bin/distrobox")
if [[ -x "$DB_CMD" ]]; then
    if _container_exists; then
        ok "Contenedor '$CONTAINER_NAME' ya existe"
    else
        warn "Contenedor '$CONTAINER_NAME' no encontrado"
        ask "¿Crear el contenedor Kali Linux mínimo ahora? (~300MB) [S/n]"
        read -r resp
        if [[ ! "$resp" =~ ^[nN]$ ]]; then
            echo "     Creando contenedor — esto puede tardar varios minutos..."
            "$DB_CMD" create \
                --name "$CONTAINER_NAME" \
                --image docker.io/kalilinux/kali-rolling:latest \
                --no-entry \
                --home "$HOME/.local/share/distrobox/$CONTAINER_NAME" \
                && ok "Contenedor '$CONTAINER_NAME' creado" || {
                    err "No se pudo crear el contenedor"
                    echo "     Créalo manualmente:"
                    echo "     distrobox create --name $CONTAINER_NAME --image docker.io/kalilinux/kali-rolling:latest --no-entry"
                }
            if _container_exists; then
                echo "     Inicializando contenedor (primera ejecución)..."
                "$DB_CMD" enter "$CONTAINER_NAME" -- bash -c \
                    "sudo apt-get update -qq && sudo apt-get install -y --no-install-recommends curl wget nmap netcat-traditional 2>/dev/null; echo done" \
                    2>/dev/null || warn "Inicialización parcial — el contenedor funciona pero puede necesitar 'apt update' manual"
            fi
        else
            warn "Contenedor omitido. Créalo después:"
            echo "     distrobox create --name $CONTAINER_NAME --image docker.io/kalilinux/kali-rolling:latest --no-entry"
        fi
    fi
else
    warn "Distrobox no disponible, saltando verificación de contenedor"
fi

hdr "6/6  Instalando $APP_NAME..."
REQUIRED=("main.py" "db.py" "checker.py" "dockshade_tools.json")
for f in "${REQUIRED[@]}"; do
    if [[ ! -f "$SCRIPT_DIR/$f" ]]; then
        err "Archivo requerido no encontrado: $SCRIPT_DIR/$f"
        exit 1
    fi
done

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
cp "$SCRIPT_DIR/main.py"              "$INSTALL_DIR/main.py"
cp "$SCRIPT_DIR/db.py"                "$INSTALL_DIR/db.py"
cp "$SCRIPT_DIR/checker.py"           "$INSTALL_DIR/checker.py"
cp "$SCRIPT_DIR/dockshade_tools.json" "$INSTALL_DIR/dockshade_tools.json"
ok "Archivos copiados a $INSTALL_DIR"

cat > "$BIN_PATH" << WRAPPER
#!/usr/bin/env bash
if [[ "\${1:-}" == "--remove" ]]; then
    exec "$SCRIPT_DIR/install.sh" --remove
fi
exec python3 "$INSTALL_DIR/main.py" "\$@"
WRAPPER
chmod +x "$BIN_PATH"
ok "Binario creado: $BIN_PATH"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR no está en tu PATH"
    SHELL_RC=""
    [[ -f "$HOME/.zshrc"  ]] && SHELL_RC="$HOME/.zshrc"
    [[ -f "$HOME/.bashrc" ]] && SHELL_RC="$HOME/.bashrc"
    if [[ -n "$SHELL_RC" ]]; then
        echo ""                                          >> "$SHELL_RC"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
        ok "PATH actualizado en $SHELL_RC"
        warn "Ejecuta: source $SHELL_RC"
    else
        warn "Agrega a tu shell rc: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  ✓  DockShade instalado          ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════╝${NC}"
echo ""
echo -e "  Ejecuta con:  ${BOLD}dockshade${NC}"
echo -e "  Desinstala:   ${BOLD}dockshade --remove${NC}"
echo ""
