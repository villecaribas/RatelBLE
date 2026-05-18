#!/usr/bin/env python3
"""
Deploy para MicroPython (ESP32) via mpremote.

Recursos:
- Conecta automaticamente: mpremote connect auto
- Envia apenas arquivos rastreados pelo Git (respeita .gitignore) OU arquivos passados via --file
- --file / -f  : faz upload de um ou mais arquivos específicos (pode repetir a flag)
- --dry-run    : mostra ações sem executá-las
- --mirror     : apaga na placa o que NÃO está no Git (escopo seguro) [ignorado se --file]
- --mirror-all : modo mirror agressivo (apaga tudo fora do Git) [ignorado se --file]
- Cria pastas necessárias antes do upload
- Remove primeiro arquivos, depois pastas vazias (ordem correta)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

MPREMOTE_BASE = ["mpremote", "connect", "auto"]  # auto-detecta a primeira placa

REMOTE_WALK_CODE = r"""
import os
def walk(d):
    try:
        names = os.listdir(d)
    except OSError:
        return
    for name in names:
        p = d + '/' + name if d != '/' else '/' + name
        is_dir = False
        try:
            os.listdir(p)
            is_dir = True
        except OSError:
            is_dir = False
        print(('D' if is_dir else 'F') + ' ' + p[1:])  # sem barra inicial
        if is_dir:
            walk(p)
walk('/')
"""

def run(cmd, check=True, capture=False):
    if capture:
        return subprocess.check_output(cmd)
    r = subprocess.run(cmd, check=check)
    return r

def git_tracked_files():
    try:
        out = subprocess.check_output(["git", "ls-files", "-z"])
    except subprocess.CalledProcessError:
        print("❌ Este diretório não parece ser um repositório Git.", file=sys.stderr)
        sys.exit(1)
    files = [p for p in out.decode("utf-8").split("\x00") if p]
    files = [f for f in files if Path(f).is_file()]
    return files

def ensure_remote_dirs(dirs, dry_run=False):
    # Cria pastas por profundidade crescente
    for d in sorted(dirs, key=lambda x: x.count("/")):
        if not d or d == ".":
            continue
        if dry_run:
            print(f"DRY-RUN 📁 mkdir :{d}")
        else:
            run(MPREMOTE_BASE + ["mkdir", f":{d}"], check=False)  # ignora erro se já existe

def copy_pairs(pairs, dry_run=False):
    # pairs: [(local_path, remote_dest_posix), ...]
    for local, dest in pairs:
        if dry_run:
            print(f"DRY-RUN 📤 {local} -> :{dest}")
        else:
            print(f"📤 {local} -> :{dest}")
            run(MPREMOTE_BASE + ["cp", local, f":{dest}"], check=True)

def list_remote_tree():
    try:
        out = subprocess.check_output(MPREMOTE_BASE + ["exec", REMOTE_WALK_CODE])
    except subprocess.CalledProcessError:
        print("❌ Falha ao listar arquivos remotos (conexão?).", file=sys.stderr)
        sys.exit(1)
    lines = out.decode("utf-8", errors="ignore").splitlines()
    r_files, r_dirs = set(), set()
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        kind, path = line[0], line[2:]
        path = path.strip("/")
        if not path:
            continue
        if kind == "F":
            r_files.add(path)
        elif kind == "D":
            r_dirs.add(path)
    return r_files, r_dirs

def remove_remote_paths(files_to_remove, dirs_to_remove, dry_run=False):
    # Remove arquivos primeiro
    for f in sorted(files_to_remove, key=lambda x: x.count("/"), reverse=True):
        if dry_run:
            print(f"DRY-RUN 🗑️ rm :{f}")
        else:
            print(f"🗑️ rm :{f}")
            run(MPREMOTE_BASE + ["rm", f":{f}"], check=False)

    # Depois pastas (da mais profunda para a raiz)
    for d in sorted(dirs_to_remove, key=lambda x: x.count("/"), reverse=True):
        if dry_run:
            print(f"DRY-RUN 🗑️ rmdir :{d}")
        else:
            print(f"🗑️ rmdir :{d}")
            run(MPREMOTE_BASE + ["rmdir", f":{d}"], check=False)

def local_to_dest(local_path: str) -> str:
    """Converte um caminho local para destino POSIX na placa.
    - Se estiver dentro do diretório atual, mantém o caminho relativo.
    - Se estiver fora, usa apenas o nome do arquivo.
    """
    p = Path(local_path)
    try:
        rel = p.resolve().relative_to(Path.cwd().resolve())
        return str(rel).replace(os.sep, "/")
    except Exception:
        return p.name  # fallback seguro

def build_dirs_from_dests(dests):
    dirs = set()
    for d in dests:
        parent = os.path.dirname(d)
        while parent and parent != ".":
            dirs.add(parent)
            parent = os.path.dirname(parent)
    return dirs

def main():
    ap = argparse.ArgumentParser(description="Deploy de projeto MicroPython para ESP32 com mpremote.")
    ap.add_argument("--dry-run", action="store_true", help="Mostra as ações sem executá-las.")
    ap.add_argument("--mirror", action="store_true", help="Remove da placa arquivos/pastas que não estão no Git (escopo seguro).")
    ap.add_argument("--mirror-all", action="store_true", help="Modo mirror agressivo: remove TUDO que não está no Git (cuidado!).")
    ap.add_argument("--verbose", action="store_true", help="Mostra mais detalhes.")
    ap.add_argument("-f", "--file", dest="files", action="append",
                    help="Arquivo específico para fazer upload (pode repetir a flag).")
    args = ap.parse_args()

    # MODO 1: Upload de arquivos específicos (sem Git)
    if args.files:
        # Aviso sobre flags ignoradas
        if args.mirror or args.mirror_all:
            print("ℹ️  Aviso: --mirror/--mirror-all são ignorados quando --file é usado.")
        # Validação de arquivos
        locals_ok = []
        for f in args.files:
            if not Path(f).is_file():
                print(f"❌ Arquivo não encontrado: {f}", file=sys.stderr)
                sys.exit(1)
            locals_ok.append(f)

        # Monta pares (local -> destino) e cria pastas necessárias
        pairs = []
        dests = []
        for lp in locals_ok:
            dest = local_to_dest(lp)
            pairs.append((lp, dest))
            dests.append(dest)

        need_dirs = build_dirs_from_dests(dests)
        ensure_remote_dirs(sorted(need_dirs), dry_run=args.dry_run)
        copy_pairs(pairs, dry_run=args.dry_run)

        if args.dry_run:
            print("\n✅ DRY-RUN concluído (nada foi modificado).")
        else:
            print("\n✅ Upload específico concluído.")
        return

    # MODO 2: Fluxo Git (respeita .gitignore) + opções de mirror
    tracked = git_tracked_files()
    if not tracked:
        print("⚠️ Nenhum arquivo rastreado pelo Git encontrado para enviar.")
        return

    git_files = sorted(set(f.replace(os.sep, "/") for f in tracked))
    git_dirs = set()
    for f in git_files:
        parent = os.path.dirname(f)
        while parent and parent != ".":
            git_dirs.add(parent)
            parent = os.path.dirname(parent)

    # Cria pastas e envia arquivos (pares local->dest são 1:1)
    ensure_remote_dirs(sorted(git_dirs), dry_run=args.dry_run)
    copy_pairs([(f, f) for f in git_files], dry_run=args.dry_run)

    # Mirror opcional
    if args.mirror or args.mirror_all:
        remote_files, remote_dirs = list_remote_tree()
        if args.mirror_all:
            files_to_remove = remote_files - set(git_files)
            preserve_dirs = git_dirs
            dirs_to_remove = remote_dirs - preserve_dirs
        else:
            top_levels = {p.split("/", 1)[0] for p in git_files}
            top_level_files = {p for p in git_files if "/" not in p}

            def in_scope(path: str) -> bool:
                if "/" in path:
                    head = path.split("/", 1)[0]
                    return head in top_levels
                else:
                    return path in top_level_files

            files_to_remove = {f for f in remote_files if in_scope(f) and f not in set(git_files)}
            needed_dirs = git_dirs
            dirs_to_remove = {d for d in remote_dirs if in_scope(d) and d not in needed_dirs}

        if args.verbose or args.dry_run:
            print("\n--- Mirror preview ---" if args.dry_run else "\n--- Mirror ---")
            print(f"Remover arquivos: {len(files_to_remove)}")
            print(f"Remover pastas  : {len(dirs_to_remove)}")

        remove_remote_paths(files_to_remove, dirs_to_remove, dry_run=args.dry_run)

    if args.dry_run:
        print("\n✅ DRY-RUN concluído (nada foi modificado).")
    else:
        print("\n✅ Deploy concluído.")

if __name__ == "__main__":
    main()
