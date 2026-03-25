#!/usr/bin/env bash
# Shim: delegates to globally installed pf CLI.
exec pf hooks context-breaker
