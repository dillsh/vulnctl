#!/bin/bash
# Compile proto files from cve-gRPC repository.
# Usage: ./scripts/proto_compile.sh
#        POINT=dev/2.0.0 ./scripts/proto_compile.sh   (pin to specific tag)

set -eu

ROOT_DIR=$(pwd)
export PYTHON_PACKAGE_NAME=src.contracts.gRPC.compiled
POINT=${POINT:-"v4.1.0"}

PROTO_DIR=src/contracts/gRPC
REPO_NAME=cve-gRPC
OUT_DIR=$PROTO_DIR/compiled
mkdir -p "$OUT_DIR"

cd "$PROTO_DIR"
git clone git@github.com:dillsh/$REPO_NAME.git
cd "$REPO_NAME"
git fetch --tags
git switch --detach "$POINT"
cd "$ROOT_DIR"

uv run python -m grpc_tools.protoc \
  --proto_path="$PROTO_DIR/$REPO_NAME" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/$REPO_NAME"/cve/v1/*.proto

rm -rf "${PROTO_DIR:?}/${REPO_NAME:?}"

# Fix relative imports to use the full package path
if [[ "$OSTYPE" == "darwin"* ]]; then
  find "$OUT_DIR" -name '*.py' -exec sed -i '' -E \
    "/from (google|grpc)/! s/from /from ${PYTHON_PACKAGE_NAME}./g" {} \;
else
  find "$OUT_DIR" -name '*.py' -exec sed -i -E \
    "/from (google|grpc)/! s/from /from ${PYTHON_PACKAGE_NAME}./g" {} \;
fi

unset PYTHON_PACKAGE_NAME
echo "Proto compilation complete → $OUT_DIR"
