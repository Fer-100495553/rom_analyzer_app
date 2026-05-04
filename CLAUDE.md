# ROM Analyzer — Project Rules

## Do NOT modify
- `data_processing.py` (except adding new functions)
- `segmentation.py`
- `plotting.py`
- `tests/`

## Project info
- Python desktop app using CustomTkinter
- Reads .c3d files from Vicon Nexus via ezc3d
- Always activate venv before running: `venv\Scripts\activate`
- Run with: `python main.py`
- Tests: `python -m pytest tests/ -v`

## Git
- Remote: https://github.com/Fer-100495553/rom-analyzer.git
- Branch: main
- Always commit and push after completing a feature

## Code style
- UI strings must use `t()` from translations.py for i18n support
- Settings persist via settings_manager.py
- venv/, data_c3d/, .settings.json are in .gitignore
