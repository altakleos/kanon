"""Aspect manifest loader — reads sibling manifest.yaml (ADR-0055)."""
from importlib.resources import files

import yaml

MANIFEST = yaml.safe_load(files(__package__).joinpath("manifest.yaml").read_text("utf-8"))
