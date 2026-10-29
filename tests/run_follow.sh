#!/bin/sh
# テスト用データだけを使う。インストール・チューナーへのアクセス・生成済みオブジェクトの変更は行わない。
set -eu
cd "$(dirname "$0")/.."
build_dir=$(mktemp -d /tmp/epgdump-follow-tests.XXXXXX)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
cc=${CC:-cc}
flags='-std=c99 -D_POSIX_C_SOURCE=200809L -O1 -g -Wno-deprecated-declarations'
if [ "${SANITIZE:-0}" = 1 ]; then flags="$flags -fsanitize=address,undefined -fno-omit-frame-pointer"; fi
libs=""
case "$(uname -s)" in Darwin) libs="-liconv";; esac
for source in eit sdt util ts aribstr; do $cc $flags -c "$source.c" -o "$build_dir/$source.o"; done
$cc $flags -Dmain=epgdump_main -c epgdump.c -o "$build_dir/epgdump.o"
$cc $flags tests/eit_follow_test.c "$build_dir/"*.o $libs -o "$build_dir/eit-follow-test"
# 既存コマンドは終了まで解析ツリーを保持するため、このテスト用実装も同じ生存期間に合わせる。
ASAN_OPTIONS=detect_leaks=0 "$build_dir/eit-follow-test"
$cc $flags epgdump.c "$build_dir/eit.o" "$build_dir/sdt.o" "$build_dir/util.o" "$build_dir/ts.o" "$build_dir/aribstr.o" $libs -o "$build_dir/epgdump"
python3 tests/test_ts.py "$build_dir/epgdump"
