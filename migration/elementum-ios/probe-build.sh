#!/usr/bin/env bash
# Real upstream compilation probe. Produces no placeholder engine and runs no media.
set -euo pipefail
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'BLOCKED: a macOS host with the iPhoneOS SDK is required.' >&2
  exit 2
fi
for native_tool in xcrun go git pkg-config; do
  command -v "$native_tool" >/dev/null || { echo "BLOCKED: missing $native_tool" >&2; exit 2; }
done
native_sdk="$(xcrun --sdk iphoneos --show-sdk-path)"
native_cc="$(xcrun --sdk iphoneos --find clang)"
native_cxx="$(xcrun --sdk iphoneos --find clang++)"
native_stage="$(mktemp -d "${TMPDIR:-/tmp}/elementum-ios-probe.XXXXXX")"
export GOOS=ios GOARCH=arm64 CGO_ENABLED=1
export CC="$native_cc -arch arm64 -isysroot $native_sdk -miphoneos-version-min=11.0"
export CXX="$native_cxx -arch arm64 -isysroot $native_sdk -miphoneos-version-min=11.0"
# Never let pkg-config silently link macOS Homebrew libraries into an iOS result.
export PKG_CONFIG_PATH=''
export PKG_CONFIG_LIBDIR="$native_stage/ios-dependencies/lib/pkgconfig"
mkdir -p "$PKG_CONFIG_LIBDIR"
git init "$native_stage/engine"
git -C "$native_stage/engine" remote add origin https://github.com/elgatito/elementum.git
git -C "$native_stage/engine" fetch --depth=1 origin cdab7e2ed69122e048be158e2ebea70dbda789ee
git -C "$native_stage/engine" checkout --detach FETCH_HEAD
test "$(git -C "$native_stage/engine" rev-parse HEAD)" = cdab7e2ed69122e048be158e2ebea70dbda789ee
cd "$native_stage/engine"
go version
xcrun --sdk iphoneos --show-sdk-version
# This probes the actual Elementum engine, including its real C++ dependency graph.
# Missing iOS libtorrent/OpenSSL is expected to be a blocker, not a substituted stub.
go build -mod=readonly -buildmode=c-archive -tags shared,go_json -o "$native_stage/ElementumEngine.a" .
shasum -a 256 "$native_stage/ElementumEngine.a"
echo "C archive created at $native_stage/ElementumEngine.a; Kodi integration and device tests still pending."
