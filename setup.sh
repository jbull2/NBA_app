#!/usr/bin/env bash

mkdir -p ~/.streamlit/

cat <<EOF > ~/.streamlit/config.toml
[server]
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
EOF