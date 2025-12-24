#!/usr/bin/env bash

mkdir -p ~/.streamlit/

cat <<EOF > ~/.streamlit/config.toml
[server]
headless = true
port = $PORT
enableCORS = false
address = "0.0.0.0"
EOF