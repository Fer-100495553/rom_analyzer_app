# ROM Analyzer — Vicon Nexus

**Range of Motion Analysis for Upper Limb using Vicon Nexus C3D files**

Developed as part of a Final Degree Project (TFG) at Universidad Carlos III de Madrid (UC3M) in collaboration with the Biomechanics and Assistive Technology Unit of the Hospital Nacional de Parapléjicos (HNP).

---

## Download

[![Download Installer](https://img.shields.io/badge/Download-ROM_Analyzer_Setup_v1.0.1-blue?style=for-the-badge&logo=windows)](https://github.com/Fer-100495553/rom_analyzer_app/releases/tag/v1.0.1)

> No Python installation required. Download and run the installer.  
> **Requirements:** Windows 10/11 (64-bit)

---

## Features

- Automated ROM detection from Vicon Nexus `.c3d` files
- Supported movements:
  - Shoulder Flexion/Extension
  - Shoulder Abduction/Adduction
  - Shoulder Internal/External Rotation
  - Elbow Flexion/Extension
  - Thorax and Trunk Extended Lateral Inclination
- Continuous and individual recording modes
- Unilateral and bilateral analysis
- Interactive segmentation with manual adjustment and outlier detection
- Results table with Peak, Valley and ROM values per repetition
- Export results to Excel (`.xlsx`)
- English / Spanish interface
- Light / Dark theme

---

## TFG Context

**Title:** Analysis and Detection of Maximum Range of Motion (ROM) of the Upper Limb Using Photogrammetry (Vicon Nexus Software) in Patients with SCI and High-Back Rest Supports

This tool was developed to process and analyse upper limb kinematics recorded with the Southampton Upper Limb Model (SULM) in Vicon Nexus, as part of a clinical biomechanics study at the Hospital Nacional de Parapléjicos.

---

## Project Structure

```
rom_analyzer_app/
├── main.py                 # Entry point
├── gui.py                  # Main application UI
├── config.py               # Movement definitions and constants
├── data_processing.py      # C3D reading and angle computation
├── segmentation.py         # Peak/valley detection
├── plotting.py             # Result charts
├── translations.py         # EN/ES strings
├── settings_manager.py     # User preferences persistence
├── validation_metrics.py   # Statistical validation (ICC, Bland-Altman)
├── assets/                 # Icons and images
├── installer/              # Inno Setup script
└── requirements.txt        # Python dependencies
```

---

## Development Setup

```bash
git clone https://github.com/Fer-100495553/rom_analyzer_app.git
cd rom_analyzer_app
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Author

**Fernando García Sánchez**  
Universidad Carlos III de Madrid (UC3M)  
Hospital Nacional de Parapléjicos — Biomechanics and Assistive Technology Unit  

---

## License

This project is licensed under the [MIT License](LICENSE).
