#!/usr/bin/env bash
# Build GNU LibreDWG from source — the DWG decoder behind the `libredwg+ezdxf`
# backend of dwg2pdf.py.  Revision 0.1.0.
#
# Why build rather than install a package:
#   * Debian/Ubuntu carry no libredwg-tools package.
#   * conda-forge's libredwg is 0.11.3876, uploaded 2020-11-17 — six years
#     behind. This builds 0.14.x.
#
# THE ONE TRAP: the `jsmn` JSON parser is a git submodule. Without it the
# build dies at `src/in_json.c:54: fatal error: ../jsmn/jsmn.h`. `--recursive`
# on the clone (or the explicit submodule step below) is not optional.
#
# Verified on Ubuntu 24.04 / gcc 13 / cmake 3.28, 2 cores, ~4 minutes.
set -euo pipefail

PREFIX="${PREFIX:-/usr/local}"
SRC="${SRC:-/tmp/libredwg}"

echo "==> dependencies"
apt-get update -qq || true
apt-get install -y -qq git cmake gcc make perl pkg-config

echo "==> clone (with submodules — see THE ONE TRAP above)"
[ -d "$SRC" ] || git clone --depth 1 --recursive https://github.com/LibreDWG/libredwg.git "$SRC"
cd "$SRC"
git submodule update --init --depth 1        # belt and braces

echo "==> configure"
cmake -B build -DCMAKE_BUILD_TYPE=Release \
               -DCMAKE_INSTALL_PREFIX="$PREFIX" \
               -DLIBREDWG_LIBONLY=OFF \
               -DBUILD_SHARED_LIBS=ON

echo "==> build (this is the slow part)"
cmake --build build -j "$(nproc)"

echo "==> install"
cmake --install build
ldconfig || true

echo "==> verify"
dwg2dxf --version
echo "OK — dwg2pdf.py --probe should now list the libredwg+ezdxf backend."
