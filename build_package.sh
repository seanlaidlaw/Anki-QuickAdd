#!/usr/bin/env bash

# load virtual environment
source venv/bin/activate

# freeze and generate installer
fbs freeze
fbs installer
