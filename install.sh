#!/usr/bin/env bash
# xbot installer for Linux and macOS
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/atpaawej/xbot/main/install.sh | bash
#
# Options (via environment variables or flags):
#   INSTALL_DIR: Directory to install binary (default: $HOME/.local/bin)
#   XBOT_VERSION: Specific release tag (default: latest)
#   --local: Install from local repository checkout

set -euo pipefail

REPO="atpaawej/xbot"
DEFAULT_INSTALL_DIR="${HOME}/.local/bin"
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
VERSION="${XBOT_VERSION:-latest}"
LOCAL_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)
      LOCAL_MODE=true
      shift
      ;;
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    -h|--help)
      echo "xbot installer"
      echo "Usage: install.sh [options]"
      echo "  --local           Install from local repository build"
      echo "  --dir <path>      Specify installation directory (default: ~/.local/bin)"
      echo "  --version <tag>   Specify release version (default: latest)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Colors
if [[ -t 1 ]]; then
  BOLD="\033[1m"
  GREEN="\033[32m"
  CYAN="\033[36m"
  YELLOW="\033[33m"
  RED="\033[31m"
  RESET="\033[0m"
else
  BOLD=""
  GREEN=""
  CYAN=""
  YELLOW=""
  RED=""
  RESET=""
fi

info() {
  echo -e "${CYAN}==>${RESET} ${BOLD}$*${RESET}"
}

success() {
  echo -e "${GREEN}==>${RESET} ${BOLD}$*${RESET}"
}

warn() {
  echo -e "${YELLOW}Warning:${RESET} $*" >&2
}

error() {
  echo -e "${RED}Error:${RESET} $*" >&2
  exit 1
}

# Header banner
echo -e "${BOLD}"
echo "    __  __ ___   ____  ____  ______"
echo "    \ \/ // _ ) / __ \/_  / /_  __/"
echo "     \  // _  |/ /_/ / / /_  / /   "
echo "     /_//____/ \____/ /___/ /_/    "
echo -e "${RESET}"
echo "Autonomous AI Agent with Rich TUI & Web Intelligence"
echo "----------------------------------------------------"

# 1. Detect OS
OS_RAW="$(uname -s)"
case "${OS_RAW}" in
  Linux)
    OS="linux"
    ;;
  Darwin)
    OS="macos"
    ;;
  *)
    error "Unsupported operating system: ${OS_RAW}. For Windows, use install.ps1 in PowerShell."
    ;;
esac

# 2. Detect Architecture
ARCH_RAW="$(uname -m)"
case "${ARCH_RAW}" in
  x86_64|amd64)
    ARCH="x86_64"
    ;;
  arm64|aarch64)
    ARCH="arm64"
    ;;
  *)
    error "Unsupported architecture: ${ARCH_RAW}."
    ;;
esac

TARGET_ASSET="xbot-${OS}-${ARCH}"

# 3. Create destination directory
mkdir -p "${INSTALL_DIR}"
TARGET_BIN="${INSTALL_DIR}/xbot"

# 4. Install logic
if [ "${LOCAL_MODE}" = true ]; then
  info "Installing in local mode from current repository..."
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  LOCAL_DIST="${SCRIPT_DIR}/dist/xbot"

  if [ ! -f "${LOCAL_DIST}" ]; then
    info "Local binary not found. Building with packaging/build.py..."
    if command -v uv >/dev/null 2>&1; then
      uv run python "${SCRIPT_DIR}/packaging/build.py"
    elif command -v python3 >/dev/null 2>&1; then
      python3 "${SCRIPT_DIR}/packaging/build.py"
    else
      error "Cannot build locally: neither uv nor python3 is available."
    fi
  fi

  cp "${LOCAL_DIST}" "${TARGET_BIN}"
  chmod 755 "${TARGET_BIN}"
  success "Installed local binary to ${TARGET_BIN}"
else
  info "Detected platform: ${OS} (${ARCH})"
  info "Target asset: ${TARGET_ASSET}"

  # Determine download URL
  if [ "${VERSION}" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${TARGET_ASSET}"
  else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${TARGET_ASSET}"
  fi

  TMP_FILE="$(mktemp "${TMPDIR:-/tmp}/xbot.XXXXXX")"
  trap 'rm -f "${TMP_FILE}"' EXIT

  info "Downloading ${DOWNLOAD_URL}..."
  DOWNLOAD_SUCCESS=false

  if command -v curl >/dev/null 2>&1; then
    if curl -fsSL "${DOWNLOAD_URL}" -o "${TMP_FILE}"; then
      DOWNLOAD_SUCCESS=true
    fi
  elif command -v wget >/dev/null 2>&1; then
    if wget -qO "${TMP_FILE}" "${DOWNLOAD_URL}"; then
      DOWNLOAD_SUCCESS=true
    fi
  else
    error "Neither curl nor wget is available. Please install one of them to proceed."
  fi

  if [ "${DOWNLOAD_SUCCESS}" = false ] || [ ! -s "${TMP_FILE}" ]; then
    warn "Failed to download pre-built binary from GitHub Releases."
    
    # Check if uv is available as fallback
    if command -v uv >/dev/null 2>&1; then
      info "Falling back to installing via uv tool..."
      uv tool install --force "git+https://github.com/${REPO}.git"
      success "xbot successfully installed via uv tool!"
      exit 0
    elif command -v pipx >/dev/null 2>&1; then
      info "Falling back to installing via pipx..."
      pipx install --force "git+https://github.com/${REPO}.git"
      success "xbot successfully installed via pipx!"
      exit 0
    else
      error "Could not find a pre-compiled binary for ${TARGET_ASSET} at ${DOWNLOAD_URL}, and neither uv nor pipx was found as a fallback."
    fi
  fi

  mv "${TMP_FILE}" "${TARGET_BIN}"
  chmod 755 "${TARGET_BIN}"
  success "Successfully installed xbot to ${TARGET_BIN}"
fi

# 5. Check PATH and configure shell profile if needed
SHELL_NAME="$(basename "${SHELL:-bash}")"
PATH_CONFIGURED=false

if [[ ":$PATH:" == *":${INSTALL_DIR}:"* ]]; then
  PATH_CONFIGURED=true
fi

if [ "${PATH_CONFIGURED}" = false ]; then
  PROFILE_FILE=""
  case "${SHELL_NAME}" in
    zsh)
      PROFILE_FILE="${HOME}/.zshrc"
      ;;
    bash)
      if [ -f "${HOME}/.bashrc" ]; then
        PROFILE_FILE="${HOME}/.bashrc"
      elif [ -f "${HOME}/.bash_profile" ]; then
        PROFILE_FILE="${HOME}/.bash_profile"
      else
        PROFILE_FILE="${HOME}/.profile"
      fi
      ;;
    fish)
      PROFILE_FILE="${HOME}/.config/fish/config.fish"
      ;;
    *)
      PROFILE_FILE="${HOME}/.profile"
      ;;
  esac

  if [ -n "${PROFILE_FILE}" ]; then
    if [ "${SHELL_NAME}" = "fish" ]; then
      EXPORT_CMD="set -gx PATH \"${INSTALL_DIR}\" \$PATH"
    else
      EXPORT_CMD="export PATH=\"${INSTALL_DIR}:\$PATH\""
    fi

    echo "" >> "${PROFILE_FILE}"
    echo "# Added by xbot installer" >> "${PROFILE_FILE}"
    echo "${EXPORT_CMD}" >> "${PROFILE_FILE}"
    info "Added ${INSTALL_DIR} to PATH in ${PROFILE_FILE}"
    warn "Run: source ${PROFILE_FILE} (or restart your terminal) to activate xbot in your PATH."
  fi
fi

echo ""
success "Installation Complete!"
echo -e "You can now run: ${CYAN}xbot --version${RESET}"
echo -e "Start an interactive session: ${CYAN}xbot${RESET}"
