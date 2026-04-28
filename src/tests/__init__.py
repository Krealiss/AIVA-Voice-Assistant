"""
Конфігурація pytest
"""
import sys
import os

# Додаємо батьківську директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
