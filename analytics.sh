#!/bin/bash
cd `dirname $0`
source venv/bin/activate
exec python analytics.py
