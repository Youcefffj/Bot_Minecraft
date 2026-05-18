"""
Bot Minecraft — orchestre ViaProxy + mineflayer.

Pipeline:
    ViaProxy.jar (Java, traduit protocole 774↔775, auth Microsoft serveur)
       └── écoute sur 127.0.0.1:25568
              ↑
    bot.js (Node, mineflayer 1.21.11, mode offline local)

Pré-requis (one-shot) :
    Ajouter le compte Microsoft à ViaProxy via la console interactive :
        ./jre/bin/java -jar ViaProxy.jar cli \
            --target-address "$SERVER_HOST:$SERVER_PORT"
        > account add microsoft        # suivre le device-code
        > exit
    (export SERVER_HOST/SERVER_PORT depuis .env, ou remplace par les valeurs.)
    Une fois fait, saves.json contient le compte et ce script peut tourner.
"""

import json
import os
import socket
import subprocess
import sys
import time

from dotenv import load_dotenv
from mcstatus import JavaServer

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

try:
    SERVER_HOST = os.environ["SERVER_HOST"]
    SERVER_PORT = int(os.environ["SERVER_PORT"])
except KeyError as e:
    sys.exit(f"Variable manquante dans .env : {e.args[0]} (voir .env.example)")

BOT_USERNAME = os.environ.get("BOT_USERNAME", "Bot")

PROXY_BIND = "127.0.0.1"
PROXY_PORT = 25568

JAVA_BIN = os.path.join(HERE, "jre", "bin", "java")
VIAPROXY_JAR = os.path.join(HERE, "ViaProxy.jar")
SAVES_FILE = os.path.join(HERE, "saves.json")

PROXY_READY_TIMEOUT_S = 30


def check_server() -> bool:
    """Ping serveur réel pour fail-fast si injoignable."""
    try:
        server = JavaServer.lookup(f"{SERVER_HOST}:{SERVER_PORT}")
        status = server.status()
        print(
            f"Serveur joignable — {status.version.name} "
            f"(protocole {status.version.protocol}), "
            f"{status.players.online}/{status.players.max} joueurs"
        )
        return True
    except Exception as e:
        print(f"Serveur injoignable : {e}")
        return False


def check_viaproxy_account() -> bool:
    """Vérifie qu'au moins un compte est enregistré dans saves.json."""
    if not os.path.exists(SAVES_FILE):
        print(f"saves.json absent — lance d'abord ViaProxy interactif pour ajouter le compte.")
        return False
    try:
        with open(SAVES_FILE) as f:
            data = json.load(f)
        if not data.get("accountsV4"):
            print("Aucun compte dans saves.json.")
            print("Lance :")
            print(f"  {JAVA_BIN} -jar ViaProxy.jar cli --target-address {SERVER_HOST}:{SERVER_PORT}")
            print("Puis dans la console : account add microsoft")
            return False
        return True
    except Exception as e:
        print(f"saves.json illisible : {e}")
        return False


def wait_for_port(host: str, port: int, timeout: float) -> bool:
    """Poll le port TCP jusqu'à connexion réussie ou timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    if not os.path.isfile(JAVA_BIN):
        print(f"JRE introuvable à {JAVA_BIN}")
        return 1
    if not os.path.isfile(VIAPROXY_JAR):
        print(f"ViaProxy.jar introuvable à {VIAPROXY_JAR}")
        return 1
    if not check_server():
        return 1
    if not check_viaproxy_account():
        return 1

    if not os.path.isdir(os.path.join(HERE, "node_modules")):
        print("Installation de mineflayer...")
        subprocess.check_call(["npm", "install"], cwd=HERE)

    # Lancement de ViaProxy en arrière-plan. On garde stdout/stderr pour debug
    # mais on suppress son output sauf en cas d'erreur (ça flood la console).
    print("Démarrage de ViaProxy...")
    proxy = subprocess.Popen(
        [
            JAVA_BIN, "-jar", VIAPROXY_JAR, "cli",
            "--target-address", f"{SERVER_HOST}:{SERVER_PORT}",
            "--bind-address", f"{PROXY_BIND}:{PROXY_PORT}",
            "--auth-method", "ACCOUNT",
            "--minecraft-account-index", "0",
        ],
        cwd=HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )

    try:
        if not wait_for_port(PROXY_BIND, PROXY_PORT, PROXY_READY_TIMEOUT_S):
            print(f"ViaProxy n'a pas ouvert le port {PROXY_PORT} en {PROXY_READY_TIMEOUT_S}s")
            return 1
        print(f"ViaProxy prêt sur {PROXY_BIND}:{PROXY_PORT}")

        return subprocess.call(["node", "bot.js"], cwd=HERE)
    finally:
        print("Arrêt de ViaProxy...")
        proxy.terminate()
        try:
            proxy.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proxy.kill()


if __name__ == "__main__":
    sys.exit(main())
